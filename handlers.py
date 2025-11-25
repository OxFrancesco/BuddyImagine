import uuid
import io
from PIL import Image
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from typing import Optional
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.fal import FalService
from services.r2 import R2Service
from services.convex import ConvexService
from agent import agent

class GenState(StatesGroup):
    selecting_model = State()

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
        "Hello! I can generate images for you using FAL AI.\n\n"
        "**Commands:**\n"
        "/generate &lt;prompt&gt; - Create an image\n"
        "/models [query] - List or search models\n"
        "/setmodel &lt;model_id&gt; - Set default model\n"
        "/credits - View balance & transactions\n"
        "/settings - View/update preferences\n"
        "/clear - Clear conversation history\n"
        "/help - Show this message\n\n"
        "💡 Chat naturally and I'll remember our conversation!",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@router.message(Command("credits"))
async def cmd_credits(message: Message):
    """Show credit balance and recent transactions."""
    if not message.from_user:
        return
    
    if not convex_service:
        await message.answer("Service unavailable.")
        return

    summary = convex_service.get_credit_summary(message.from_user.id)
    if not summary:
        await message.answer("User not found. Use /start to register.")
        return

    history = convex_service.get_credit_history(message.from_user.id, limit=5)
    
    response = f"💰 **Credit Balance**: {summary['current_balance']:.2f} credits\n\n"
    response += f"📊 **Statistics**:\n"
    response += f"  • Total spent: {summary['total_spent']:.2f} credits\n"
    response += f"  • Total added: {summary['total_added']:.2f} credits\n"
    response += f"  • Generations: {summary['generation_count']}\n\n"
    
    if history:
        response += "📜 **Recent Transactions**:\n"
        for log in history[:5]:
            amount_str = f"+{log['amount']:.2f}" if log['amount'] > 0 else f"{log['amount']:.2f}"
            response += f"  • {amount_str} - {log['description']}\n"
    
    response += "\n_Use /credithistory for full transaction log._"
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("credithistory"))
async def cmd_credithistory(message: Message):
    """Show full credit transaction history."""
    if not message.from_user:
        return
    
    if not convex_service:
        await message.answer("Service unavailable.")
        return

    history = convex_service.get_credit_history(message.from_user.id, limit=20)
    
    if not history:
        await message.answer("No transaction history found.")
        return

    response = "📜 **Credit History** (last 20):\n\n"
    for log in history:
        amount_str = f"+{log['amount']:.2f}" if log['amount'] > 0 else f"{log['amount']:.2f}"
        response += f"• {amount_str} | {log['type']} | {log['description']}\n"
    
    await message.answer(response, parse_mode="Markdown")


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """View or update user settings."""
    if not message.from_user or not message.text:
        return
    
    if not convex_service:
        await message.answer("Service unavailable.")
        return

    args = message.text.replace("/settings", "", 1).strip().split()
    user_id = message.from_user.id
    
    if not args:
        settings = convex_service.get_user_settings(user_id)
        if not settings:
            await message.answer("User not found. Use /start to register.")
            return
        
        storage_status = "ON (+10% cost)" if settings.get("save_uncompressed_to_r2") else "OFF"
        quality = settings.get("telegram_quality", "uncompressed")
        notify = "ON" if settings.get("notify_low_credits", True) else "OFF"
        threshold = settings.get("low_credit_threshold", 10)
        
        response = "⚙️ **Your Settings**:\n\n"
        response += f"📱 Telegram quality: `{quality}`\n"
        response += f"💾 Uncompressed R2 storage: `{storage_status}`\n"
        response += f"🔔 Low credit notification: `{notify}` (threshold: {threshold})\n"
        response += f"🤖 Default model: `{settings.get('default_model', 'fal-ai/fast-sdxl')}`\n\n"
        response += "**Commands**:\n"
        response += "`/settings quality compressed|uncompressed`\n"
        response += "`/settings storage on|off` (+10% cost when on)\n"
        response += "`/settings notify on|off`\n"
        response += "`/settings threshold <number>`"
        await message.answer(response, parse_mode="Markdown")
        return

    setting_name = args[0].lower()
    setting_value = args[1].lower() if len(args) > 1 else None

    if setting_name == "quality":
        if setting_value not in ["compressed", "uncompressed"]:
            await message.answer("Usage: /settings quality compressed|uncompressed")
            return
        convex_service.update_user_settings(user_id, telegram_quality=setting_value)
        await message.answer(f"✅ Telegram quality set to: `{setting_value}`", parse_mode="Markdown")

    elif setting_name == "storage":
        if setting_value not in ["on", "off"]:
            await message.answer("Usage: /settings storage on|off")
            return
        enabled = setting_value == "on"
        convex_service.update_user_settings(user_id, save_uncompressed_to_r2=enabled)
        status = "ON (+10% cost per generation)" if enabled else "OFF"
        await message.answer(f"✅ Uncompressed R2 storage: `{status}`", parse_mode="Markdown")

    elif setting_name == "notify":
        if setting_value not in ["on", "off"]:
            await message.answer("Usage: /settings notify on|off")
            return
        enabled = setting_value == "on"
        convex_service.update_user_settings(user_id, notify_low_credits=enabled)
        await message.answer(f"✅ Low credit notifications: `{'ON' if enabled else 'OFF'}`", parse_mode="Markdown")

    elif setting_name == "threshold":
        if not setting_value or not setting_value.replace(".", "").isdigit():
            await message.answer("Usage: /settings threshold <number>")
            return
        threshold = float(setting_value)
        convex_service.update_user_settings(user_id, low_credit_threshold=threshold)
        await message.answer(f"✅ Low credit threshold set to: `{threshold}` credits", parse_mode="Markdown")

    else:
        await message.answer("Unknown setting. Use /settings to see available options.")


@router.message(Command("clear"))
async def cmd_clear(message: Message):
    """Clear conversation history for the user."""
    if not message.from_user:
        return
    
    if convex_service:
        result = convex_service.clear_messages(message.from_user.id)
        await message.answer(f"🗑️ Conversation history cleared ({result.get('deleted', 0)} messages deleted).")
    else:
        await message.answer("❌ Service unavailable.")

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

@router.message(Command("setmodel"))
async def cmd_setmodel(message: Message):
    if not message.text:
        return

    query = message.text.replace("/setmodel", "", 1).strip()
    
    if not query:
        await message.answer("Please provide a model ID or name. Usage: /setmodel <query>\nExample: `/setmodel flux`", parse_mode="Markdown")
        return

    # Fuzzy search
    matches = fal_service.search_models(query)
    
    if not matches:
        await message.answer(f"❌ No models found matching '{query}'. Use /models to see available ones.")
        return

    # If exact match or only one result
    if len(matches) == 1:
        model_id = matches[0]['id']
        await set_user_model(message, model_id)
        return

    # If multiple matches, show buttons
    keyboard = []
    for model in matches[:5]: # Limit to top 5
        keyboard.append([InlineKeyboardButton(text=f"{model['name']} ({model['id']})", callback_data=f"set_model:{model['id']}")])
    
    await message.answer(
        f"🤔 I found multiple models matching '{query}'. Please choose one:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

async def set_user_model(message: Message, model_id: str):
    if not convex_service:
        await message.answer("❌ Service unavailable.")
        return

    if not message.from_user:
        await message.answer("❌ Could not identify user.")
        return

    try:
        convex_service.set_default_model(message.from_user.id, model_id)
        await message.answer(f"✅ Default model set to: `{model_id}`", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Failed to set model: {str(e)}")

@router.callback_query(F.data.startswith("set_model:"))
async def process_setmodel_callback(callback: CallbackQuery):
    if not callback.data or not callback.message or not isinstance(callback.message, Message):
        return

    model_id = callback.data.split(":")[1]
    # We need to construct a fake message object or refactor set_user_model to take user_id directly
    # But passing message is easier for now since we need to reply.
    # We can use callback.message but we need to ensure from_user is correct (it's the user who clicked).
    
    # Actually, callback.from_user is the user who clicked.
    # callback.message is the message the button was attached to (bot's message).
    
    if not convex_service:
        await callback.answer("Service unavailable", show_alert=True)
        return

    try:
        convex_service.set_default_model(callback.from_user.id, model_id)
        await callback.message.edit_text(f"✅ Default model set to: `{model_id}`", parse_mode="Markdown")
        await callback.answer("Model set!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Failed to set model: {str(e)}")

@router.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext):
    if not message.text:
        return

    # Extract prompt
    prompt = message.text.replace("/generate", "", 1).strip()
    
    if not prompt:
        await message.answer("Please provide a prompt. Usage: /generate &lt;prompt&gt;")
        return

    status_msg = await message.answer("🤖 Agent is thinking and working...")

    # Default model if not specified (agent might pick another, but we need a baseline for credit check)
    # Check for "using <model>" pattern
    full_text = prompt
    target_model_query = None
    
    if " using " in full_text.lower():
        parts = full_text.lower().split(" using ")
        # Assume the last part is the model query if it's short enough, otherwise it might be part of prompt
        potential_model = parts[-1].strip()
        if len(potential_model) < 50: # Heuristic
            target_model_query = potential_model
            prompt = " using ".join(parts[:-1]).strip() # Reconstruct prompt without the model part

    # If user specified a model, search for it
    selected_model_id = None
    
    if target_model_query:
        matches = fal_service.search_models(target_model_query)
        
        if not matches:
            await message.answer(f"🤔 I couldn't find a model matching '{target_model_query}'. Using default.")
            # Fallback to default logic (handled in run_generation)
        elif len(matches) == 1:
            selected_model_id = matches[0]['id']
        else:
            # Ambiguous match - Ask user
            keyboard = []
            for model in matches[:5]:
                keyboard.append([InlineKeyboardButton(text=f"{model['name']} ({model['id']})", callback_data=f"gen_model:{model['id']}")])
            
            await state.update_data(prompt=prompt)
            await state.set_state(GenState.selecting_model)
            
            await message.answer(
                f"🤔 Multiple models found for '{target_model_query}'. Which one?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            return

    # Proceed to generation
    user_id = message.from_user.id if message.from_user else message.chat.id
    await run_generation_safe(message, prompt, selected_model_id, user_id)

@router.callback_query(F.data.startswith("gen_model:"), GenState.selecting_model)
async def process_gen_model_callback(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.message or not isinstance(callback.message, Message):
        return

    model_id = callback.data.split(":")[1]
    data = await state.get_data()
    prompt = data.get("prompt")
    
    if not isinstance(prompt, str):
        await callback.answer("Session expired or invalid data.")
        return

    await state.clear()
    await callback.message.delete() # Remove selection menu
    
    # We need to send a new message as "status_msg" because run_generation expects to reply to a message
    # We can use callback.message but it was deleted. Let's send a new one or use callback.message.answer
    # Actually run_generation takes 'message' and calls answer().
    # We can pass callback.message but we need to ensure from_user is correct (it's the user who clicked).
    # Better: Send a "Starting..." message and pass that? No, run_generation creates its own status msg.
    # We just need a Message object to call answer() on. callback.message works for that context.
    
    await run_generation_safe(callback.message, prompt, model_id, callback.from_user.id)

async def run_generation_safe(message: Message, prompt: str, model_id: str | None, user_id: int):
    status_msg = await message.answer("🤖 Agent is thinking and working...")
    
    # Get user settings
    user_settings: dict = {}
    if convex_service:
        user_settings = convex_service.get_user_settings(user_id) or {}
        user_credits = user_settings.get("credits", 0)
        if user_credits <= 0:
            await status_msg.edit_text("❌ You have 0 credits. Please contact admin to top up.")
            return

    # Track cost for deduction
    deducted_credits = 0.0
    r2_filename = ""

    try:
        # Determine Model ID if not set
        if not model_id:
            model_id = user_settings.get("default_model", "fal-ai/fast-sdxl")

            # Simple keyword overrides (legacy support if user didn't use "using")
            if "flux" in prompt.lower():
                model_id = "fal-ai/flux/dev"
            elif "video" in prompt.lower():
                model_id = "fal-ai/hunyuan-video-v1.5/text-to-video"
            elif "fast" in prompt.lower() and "flux" not in prompt.lower():
                model_id = "fal-ai/fast-sdxl"
        
        # Estimate Cost with 15% markup
        api_cost = fal_service.estimate_cost(model_id)
        credits_needed = (api_cost / 0.10) * 1.15  # 15% markup
        
        # Check if user wants uncompressed R2 storage (+10%)
        save_uncompressed_to_r2 = user_settings.get("save_uncompressed_to_r2", False)
        if save_uncompressed_to_r2:
            credits_needed *= 1.10  # +10% for uncompressed R2 storage

        # Deduct Credits with logging
        if convex_service:
            description = f"Generation: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            result = convex_service.deduct_credits_with_log(
                telegram_id=user_id,
                amount=credits_needed,
                log_type="generation",
                description=description,
                model_used=model_id,
            )
            if not result or not result.get("success"):
                await status_msg.edit_text(
                    f"❌ Insufficient credits. Needed: {credits_needed:.2f}, Available: {result.get('current_credits', 0):.2f}"
                )
                return
            
            deducted_credits = credits_needed
            storage_note = " (+R2 full quality)" if save_uncompressed_to_r2 else ""
            await status_msg.edit_text(
                f"🎨 Generating with {model_id}...\n💰 Cost: {credits_needed:.2f} credits{storage_note}"
            )

        # Clean prompt (remove model/quality keywords for better generation)
        clean_prompt = prompt
        for keyword in ["using model", "uncompressed", "high quality", "original quality"]:
            clean_prompt = clean_prompt.lower().replace(keyword, "").strip()

        # Direct generation (no agent)
        image_data = await fal_service.generate_image(clean_prompt, model=model_id)
        
        # Process image
        img = Image.open(io.BytesIO(image_data))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Create compressed version for R2 (default)
        compressed_buffer = io.BytesIO()
        img.save(compressed_buffer, format="JPEG", quality=60, optimize=True)
        compressed_data = compressed_buffer.getvalue()
        
        # Upload compressed to R2
        r2_filename = f"{uuid.uuid4()}.jpg"
        await r2_service.upload_file(compressed_data, r2_filename)
        
        # If user has uncompressed R2 storage enabled, also save full quality
        if save_uncompressed_to_r2:
            uncompressed_buffer = io.BytesIO()
            img.save(uncompressed_buffer, format="JPEG", quality=95)
            uncompressed_data = uncompressed_buffer.getvalue()
            full_filename = r2_filename.replace(".jpg", "_full.jpg")
            await r2_service.upload_file(uncompressed_data, full_filename)
        
        # Determine what to send to Telegram based on user settings
        telegram_quality = user_settings.get("telegram_quality", "uncompressed")
        if telegram_quality == "compressed":
            telegram_image_data = compressed_data
        else:
            # Default: send uncompressed to Telegram
            uncompressed_buffer = io.BytesIO()
            img.save(uncompressed_buffer, format="JPEG", quality=95)
            telegram_image_data = uncompressed_buffer.getvalue()

        # Send to user
        try:
            await message.answer_photo(
                BufferedInputFile(telegram_image_data, filename=r2_filename),
                caption=f"✅ Generated and saved as: {r2_filename}\n💰 Credits used: {deducted_credits:.2f}"
            )
            await status_msg.delete()
            
            # Check for low credit warning
            new_balance = convex_service.get_credits(user_id) if convex_service else 0
            threshold = user_settings.get("low_credit_threshold", 10)
            notify = user_settings.get("notify_low_credits", True)
            if notify and new_balance <= threshold:
                await message.answer(
                    f"⚠️ Low credit warning! Balance: {new_balance:.2f} credits\n"
                    f"Use /settings to adjust notification threshold."
                )
        except Exception as download_error:
            await status_msg.edit_text(
                f"✅ Agent finished: {r2_filename}\n⚠️ Failed to send image back: {str(download_error)}"
            )

    except Exception as e:
        # Refund if failed
        if convex_service and deducted_credits > 0:
            convex_service.add_credits_with_log(
                telegram_id=user_id,
                amount=deducted_credits,
                log_type="refund",
                description=f"Refund for failed generation: {str(e)[:50]}"
            )
            await message.answer(f"⚠️ Generation failed. {deducted_credits:.2f} credits have been refunded.")

        error_msg = str(e)
        if len(error_msg) > 1000:
            error_msg = error_msg[:1000] + "... (truncated)"
        await status_msg.edit_text(f"❌ Error: {error_msg}")
        print(f"FULL ERROR: {e}")

# Wrapper to adapt signatures
async def run_generation(message: Message, prompt: str, model_id: str | None = None):
    user_id = message.from_user.id if message.from_user else message.chat.id
    await run_generation_safe(message, prompt, model_id, user_id)


def build_message_history(messages: list) -> list:
    """Convert Convex messages to pydantic-ai ModelMessage format."""
    from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, TextPart
    
    history: list[ModelRequest | ModelResponse] = []
    for msg in messages:
        if msg["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=msg["content"])]))
    return history


@router.message(F.text & ~F.text.startswith("/"))
async def handle_natural_message(message: Message):
    """Handle natural language messages using the AI agent with conversation memory."""
    if not message.text or not message.from_user:
        return
    
    user_id = message.from_user.id
    user_text = message.text
    status_msg = await message.answer("🤖 Agent is thinking...")
    
    # Check credits
    if convex_service:
        user_credits = convex_service.get_credits(user_id)
        if user_credits <= 0:
            await status_msg.edit_text("❌ You have 0 credits. Please contact admin to top up.")
            return

    try:
        # Fetch conversation history
        message_history = []
        if convex_service:
            stored_messages = convex_service.get_messages(user_id, limit=20)
            message_history = build_message_history(stored_messages)
        
        # Run agent with history
        deps = {'fal_service': fal_service, 'r2_service': r2_service}
        result = await agent.run(user_text, deps=deps, message_history=message_history)
        agent_response = str(result.output)
        
        # Save conversation to Convex
        if convex_service:
            convex_service.save_message(user_id, "user", user_text)
            convex_service.save_message(user_id, "assistant", agent_response)
        
        if not agent_response or "Error" in agent_response:
            await status_msg.edit_text(f"🤖 Agent response: {agent_response}")
            return
        
        # If it looks like a filename, try to download and send the image
        if agent_response.endswith(('.jpg', '.jpeg', '.png')):
            try:
                image_data = await r2_service.download_file(agent_response)
                await message.answer_photo(
                    BufferedInputFile(image_data, filename=agent_response),
                    caption=f"✅ Generated: {agent_response}"
                )
                await status_msg.delete()
            except Exception:
                await status_msg.edit_text(f"✅ Generated: {agent_response}")
        else:
            await status_msg.edit_text(f"🤖 {agent_response}")
            
    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        await status_msg.edit_text(f"❌ Error: {error_msg}\n\n💡 Tip: Use /generate <prompt> for direct generation.")