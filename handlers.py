import uuid
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BufferedInputFile
from services.fal import FalService
from services.r2 import R2Service
from agent import agent

router = Router()
# Initialize services to pass as dependencies
fal_service = FalService()
r2_service = R2Service()

@router.message(CommandStart())
async def cmd_start(message: Message):
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

    try:
        # Run the agent
        # The agent will decide to call tools to generate and upload.
        # We expect the agent to return the filename or a confirmation message.
        deps = {
            'fal_service': fal_service,
            'r2_service': r2_service
        }
        
        result = await agent.run(prompt, deps=deps)
        
        # The result.output should contain the final response from the agent (the filename)
        filename = result.output
        
        # Download the image from R2 to send it to the user
        try:
            image_data = await r2_service.download_file(filename)
            await message.answer_photo(
                BufferedInputFile(image_data, filename=filename),
                caption=f"✅ Generated and saved as: {filename}"
            )
            await status_msg.delete() # Remove the "thinking" message
        except Exception as download_error:
             await status_msg.edit_text(f"✅ Agent finished: {filename}\n⚠️ Failed to send image back: {str(download_error)}")

    except Exception as e:
        error_msg = str(e)
        if len(error_msg) > 1000:
            error_msg = error_msg[:1000] + "... (truncated)"
        await status_msg.edit_text(f"❌ Error: {error_msg}")
        # Print full error to console for debugging
        print(f"FULL ERROR: {e}")