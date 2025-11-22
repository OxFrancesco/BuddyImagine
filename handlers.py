import uuid
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
        "Hello! I can generate images for you using FAL AI.\n"
        "Commands:\n"
        "/generate &lt;prompt&gt; - Create an image (you can specify model in prompt!)\n"
        "/models [query] - List or search available models\n"
        "/setmodel &lt;model_id&gt; - Set your default model preference\n"
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
    
    if convex_service:
        user_credits = convex_service.get_credits(user_id)
        if user_credits <= 0:
            await status_msg.edit_text("❌ You have 0 credits. Please contact admin to top up.")
            return

    # Track cost for deduction
    deducted_credits = 0.0

    try:
        # Determine Model ID if not set
        if not model_id:
            model_id = "fal-ai/fast-sdxl" # System Default
            
            # Check user preference
            if convex_service:
                 user_profile = convex_service.get_user(user_id)
                 if user_profile and user_profile.get("default_model"):
                     model_id = user_profile.get("default_model")

            # Simple keyword overrides (legacy support if user didn't use "using")
            if "flux" in prompt.lower():
                model_id = "fal-ai/flux/dev"
            elif "video" in prompt.lower():
                model_id = "fal-ai/hunyuan-video-v1.5/text-to-video"
            elif "fast" in prompt.lower() and "flux" not in prompt.lower():
                 model_id = "fal-ai/fast-sdxl"
        
        # Estimate Cost
        cost = fal_service.estimate_cost(model_id)
        credits_needed = cost / 0.10 # 1 credit = $0.10
        
        # Append model instruction if not already present
        if "using model" not in prompt.lower():
             prompt += f" using model {model_id}"
        
        # Deduct Credits
        if convex_service:
            result = convex_service.deduct_credits(user_id, credits_needed)
            if not result or not result.get("success"):
                await status_msg.edit_text(f"❌ Insufficient credits. Needed: {credits_needed:.1f}, Available: {result.get('current_credits', 0):.1f}")
                return
            
            deducted_credits = credits_needed
            await status_msg.edit_text(f"🤖 Generating with {model_id}... (Cost: {credits_needed:.1f} credits)")

        # Run Agent
        deps = {'fal_service': fal_service, 'r2_service': r2_service}
        result = await agent.run(prompt, deps=deps)
        filename = result.output
        
        if not filename or "Error" in str(filename):
             raise Exception(f"Agent failed to return a valid filename: {filename}")

        # Download and Send
        try:
            image_data = await r2_service.download_file(filename)
            await message.answer_photo(
                BufferedInputFile(image_data, filename=filename),
                caption=f"✅ Generated and saved as: {filename}\n💰 Credits used: {deducted_credits:.1f}"
            )
            await status_msg.delete()
        except Exception as download_error:
             await status_msg.edit_text(f"✅ Agent finished: {filename}\n⚠️ Failed to send image back: {str(download_error)}")

    except Exception as e:
        # Refund if failed
        if convex_service and deducted_credits > 0:
            convex_service.refund_credits(user_id, deducted_credits)
            await message.answer(f"⚠️ Generation failed. {deducted_credits:.1f} credits have been refunded.")

        error_msg = str(e)
        if len(error_msg) > 1000:
            error_msg = error_msg[:1000] + "... (truncated)"
        await status_msg.edit_text(f"❌ Error: {error_msg}")
        print(f"FULL ERROR: {e}")

# Wrapper to adapt signatures
async def run_generation(message: Message, prompt: str, model_id: str | None = None):
    user_id = message.from_user.id if message.from_user else message.chat.id
    await run_generation_safe(message, prompt, model_id, user_id)