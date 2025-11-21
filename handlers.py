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
        "Try /generate <prompt> to create an image."
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
        
        # The result.data should contain the final response from the agent (the filename or message)
        await status_msg.edit_text(f"✅ Agent finished: {result.data}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
