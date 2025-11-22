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
        "Try /generate &lt;prompt&gt; to create an image."
    )

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
