import uuid
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from typing import Optional
from aiogram.types import Message, BufferedInputFile
from services.fal import FalService
from services.r2 import R2Service
from services.convex import ConvexService
from agent import agent

router = Router()
# Initialize services to pass as dependencies
fal_service = FalService()
r2_service = R2Service()
convex_service: Optional[ConvexService] = None
try:
    convex_service = ConvexService()
except ValueError:
    print("WARNING: ConvexService not initialized. CONVEX_URL not set.")

@router.message(CommandStart())
async def cmd_start(message: Message):
    if convex_service and message.from_user:
        convex_service.upsert_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

    await message.answer(
        "Hello! I can generate images for you using FAL AI.\n"
        "Commands:\n"
        "/generate <prompt> - Create an image (you can specify model in prompt!)\n"
        "/models [query] - List or search available models\n"
        "/help - Show this help message"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)

@router.message(Command("models"))
async def cmd_models(message: Message):
    if not message.text:
        return

    query = message.text.replace("/models", "", 1).strip()
    
    if query:
        results = fal_service.search_models(query)
        if not results:
            await message.answer(f"No models found matching '{query}'.")
            return
        
        response = f"🔍 **Models matching '{query}':**\n\n"
        for model in results:
            response += f"• `{model['id']}`\n  _{model['name']}_: {model['description']}\n\n"
    else:
        # List all known models
        response = "📚 **Available Models:**\n\n"
        for model in fal_service.KNOWN_MODELS:
            response += f"• `{model['id']}`\n  _{model['name']}_: {model['description']}\n\n"
        response += "To search, use `/models <query>`."

    await message.answer(response, parse_mode="Markdown")

@router.message(Command("generate"))
async def cmd_generate(message: Message):
    if not message.text:
        return

    # Extract prompt
    prompt = message.text.replace("/generate", "", 1).strip()
    
    if not prompt:
        await message.answer("Please provide a prompt. Usage: /generate <prompt>")
        return

    status_msg = await message.answer("🤖 Agent is thinking and working...")

    # Default model if not specified (agent might pick another, but we need a baseline for credit check)
    # Ideally, we should let the agent decide, but for rate limiting we need to know beforehand or authorize a max amount.
    # For now, we'll assume a standard cost or try to parse the model from prompt if user specified it (simple heuristic).
    # A better approach: The agent returns the model it WANTS to use, we check credits, then confirm. 
    # But since the agent runs the tool directly... we might need to wrap the tool execution or check credits inside the tool.
    # HOWEVER, the requirement is to check credits.
    # Let's do a simple check based on a default "safe" cost if model isn't clear, or just deduct a standard amount.
    # Or better: The agent is "thinking", we can't easily intercept the tool call from here without modifying the agent/tools.
    # BUT, we can check if user has *some* credits before even starting the agent.
    
    if convex_service:
        if not message.from_user:
             await message.answer("❌ Could not identify user.")
             return
             
        user_credits = convex_service.get_credits(message.from_user.id)
        if user_credits <= 0:
            await message.answer("❌ You have 0 credits. Please contact admin to top up.")
            return

    status_msg = await message.answer("🤖 Agent is thinking and working...")

    # Track cost for deduction
    estimated_cost = 0.0
    deducted_credits = 0.0

    try:
        # Run the agent
        # The agent will decide to call tools to generate and upload.
        # We expect the agent to return the filename or a confirmation message.
        deps = {
            'fal_service': fal_service,
            'r2_service': r2_service
        }
        
        # NOTE: In a real robust system, the tool itself should check/deduct credits.
        # For this implementation, we will deduct AFTER successful generation based on what was likely used,
        # OR deduct a fixed amount.
        # Let's try to parse the model from the prompt to estimate cost, or use a default.
        # Since the agent decides the model, we'll assume a default cost for "standard generation" unless we see keywords.
        
        model_id = "fal-ai/fast-sdxl" # Default
        if "flux" in prompt.lower():
            model_id = "fal-ai/flux/dev"
        elif "video" in prompt.lower():
            model_id = "fal-ai/hunyuan-video-v1.5/text-to-video"
            
        cost = fal_service.estimate_cost(model_id)
        credits_needed = cost / 0.10 # 1 credit = $0.10
        
        if convex_service:
            if not message.from_user:
                 await status_msg.edit_text("❌ Could not identify user for credit deduction.")
                 return

            # Check and deduct
            result = convex_service.deduct_credits(message.from_user.id, credits_needed)
            if not result or not result.get("success"):
                await status_msg.edit_text(f"❌ Insufficient credits. Needed: {credits_needed:.1f}, Available: {result.get('current_credits', 0):.1f}")
                return
            
            deducted_credits = credits_needed
            await status_msg.edit_text(f"🤖 Generating... (Cost: {credits_needed:.1f} credits)")

        result = await agent.run(prompt, deps=deps)
        
        # The result.output should contain the final response from the agent (the filename)
        filename = result.output
        
        # Download the image from R2 to send it to the user
        try:
            image_data = await r2_service.download_file(filename)
            await message.answer_photo(
                BufferedInputFile(image_data, filename=filename),
                caption=f"✅ Generated and saved as: {filename}\n💰 Credits used: {deducted_credits:.1f}"
            )
            await status_msg.delete() # Remove the "thinking" message
        except Exception as download_error:
             await status_msg.edit_text(f"✅ Agent finished: {filename}\n⚠️ Failed to send image back: {str(download_error)}")

    except Exception as e:
        # Refund if failed
        if convex_service and deducted_credits > 0:
            if message.from_user:
                convex_service.refund_credits(message.from_user.id, deducted_credits)
                await message.answer(f"⚠️ Generation failed. {deducted_credits:.1f} credits have been refunded.")

        error_msg = str(e)
        if len(error_msg) > 1000:
            error_msg = error_msg[:1000] + "... (truncated)"
        await status_msg.edit_text(f"❌ Error: {error_msg}")
        # Print full error to console for debugging
        print(f"FULL ERROR: {e}")