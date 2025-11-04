# core/admin/handlers_log_viewer.py
import logging
from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("some_command")) 
async def some_handler(message: types.Message):
    await message.answer("You triggered some_command!")