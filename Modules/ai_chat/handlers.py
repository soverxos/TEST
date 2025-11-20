from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import asyncio

router = Router()

@router.message(Command("ask"))
async def ask_command_handler(message: types.Message):
    """
    Handle /ask command.
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /ask <question>")
        return

    question = args[1]
    
    # Mock AI response for now
    processing_msg = await message.answer("🤔 Thinking...")
    
    # Simulate delay
    await asyncio.sleep(1.5)
    
    response = f"🤖 **AI Response:**\n\nYou asked: _{question}_\n\nThis is a mock response from the AI Chat module. To make it real, configure the provider in settings!"
    
    await processing_msg.edit_text(response, parse_mode="Markdown")
