import os
import logging
import sys
import hmac
import hashlib
import uuid
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from aiogram import Bot, Dispatcher, types

# Add the project root to sys.path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imagine.bot import get_bot, get_dispatcher
from imagine.handlers import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum request size (1MB)
MAX_REQUEST_SIZE = 1024 * 1024

app = FastAPI(
    title="BuddyImagine Bot",
    docs_url=None,  # Disable docs in production
    redoc_url=None,
)

# Add trusted host middleware (configure ALLOWED_HOSTS env var)
allowed_hosts = os.getenv("ALLOWED_HOSTS", "*.vercel.app,*.buddytools.org,localhost").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


def verify_telegram_webhook(token: str, payload: bytes, secret_token: str | None) -> bool:
    """
    Verify Telegram webhook request authenticity.
    
    Telegram sends a X-Telegram-Bot-Api-Secret-Token header if configured.
    This should match the secret_token set when configuring the webhook.
    """
    if not secret_token:
        # If no secret token configured, skip verification (not recommended for production)
        logger.warning("Webhook secret token not configured - skipping verification")
        return True
    
    # Compare the provided secret token
    request_secret = secret_token
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    
    if not expected_secret:
        logger.warning("TELEGRAM_WEBHOOK_SECRET not set - skipping verification")
        return True
    
    return hmac.compare_digest(request_secret, expected_secret)


# Initialize bot and dispatcher
# Note: In a serverless environment, these might be re-initialized frequently.
try:
    bot = get_bot()
    dp = get_dispatcher()
    dp.include_router(router)
except Exception as e:
    logger.error(f"Failed to initialize bot/dispatcher: {e}")
    bot = None
    dp = None


@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    """Add request ID for tracking and logging."""
    request_id = str(uuid.uuid4())[:8]
    
    # Check request size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        return Response(content="Request too large", status_code=413)
    
    # Add request ID to state for logging
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "BuddyImagine Bot"}


@app.get("/health")
async def health_check():
    """Detailed health check with dependency status."""
    health_status = {
        "status": "ok",
        "bot_initialized": bot is not None,
        "dispatcher_initialized": dp is not None,
    }
    
    # Check if critical env vars are set
    health_status["env_check"] = {
        "telegram_token": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "fal_key": bool(os.getenv("FAL_KEY")),
        "convex_url": bool(os.getenv("CONVEX_URL")),
        "r2_configured": all([
            os.getenv("R2_ACCESS_KEY_ID"),
            os.getenv("R2_SECRET_ACCESS_KEY"),
            os.getenv("R2_BUCKET_NAME"),
        ]),
    }
    
    # Overall status
    if not bot or not dp:
        health_status["status"] = "degraded"
    
    return health_status


@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """Handle incoming Telegram updates via Webhook."""
    if not bot or not dp:
        logger.error("Bot not initialized")
        return Response(content="Bot not initialized", status_code=500)

    try:
        # Verify webhook authenticity
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not verify_telegram_webhook(
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
            b"",  # We use secret token method, not payload hash
            secret_token
        ):
            logger.warning(f"Webhook verification failed from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Get the JSON body from the request
        payload = await request.json()
        
        # Basic payload validation
        if not isinstance(payload, dict) or "update_id" not in payload:
            logger.warning("Invalid webhook payload structure")
            return {"status": "error", "message": "Invalid payload"}
        
        # Convert raw JSON to an aiogram Update object
        update = types.Update(**payload)
        
        # Feed the update to the dispatcher
        await dp.feed_update(bot=bot, update=update)
        
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(f"[{request_id}] Error processing webhook: {e}")
        # Return 200 even on error to prevent Telegram from retrying endlessly
        return {"status": "error", "message": "Internal error"}
