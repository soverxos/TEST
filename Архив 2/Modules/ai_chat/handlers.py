from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils import markdown as md
from aiogram import F
import asyncio

from Systems.core.ui.callback_data_factories import ModuleAction, ModuleMenuEntry

router = Router()


class AIChatStates(StatesGroup):
    waiting_for_prompt = State()


def _build_back_to_menu_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад к модулям",
            callback_data=ModuleMenuEntry(module_name="ai_chat").pack()
        )
    )
    return builder.as_markup()


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
    processing_msg = await message.answer("🤔 Thinking...")
    await asyncio.sleep(1.5)
    response = (
        "🤖 **AI Response:**\n\n"
        f"You asked: _{question}_\n\n"
        "This is still a mock answer. Configure a real AI provider in the module settings."
    )
    await processing_msg.edit_text(response, parse_mode="Markdown")


@router.callback_query(ModuleAction.filter(F.module_name == "ai_chat"))
async def cq_ai_chat_entry(
    query: types.CallbackQuery,
    callback_data: ModuleAction,
    state: FSMContext
):
    if callback_data.action != "execute":
        await query.answer()
        return

    await state.set_state(AIChatStates.waiting_for_prompt)
    await query.message.edit_text(
        md.text(
            "🤖 **AI Chat готов к общению!**",
            "",
            "Введите свой вопрос, а я верну ответ."
        ),
        reply_markup=_build_back_to_menu_keyboard(),
        parse_mode="Markdown"
    )
    await query.answer()


@router.message(AIChatStates.waiting_for_prompt)
async def handle_ai_prompt(message: types.Message, state: FSMContext):
    await message.answer("🔄 Запрашиваю AI...")
    await asyncio.sleep(1.5)

    response = (
        "🧠 **AI-помощник:**\n\n"
        f"You wrote: _{message.text}_\n\n"
        "Замените этот ответ на реальный вызов внешнего API, если нужно."
    )

    await message.answer(response, parse_mode="Markdown", reply_markup=_build_back_to_menu_keyboard())
    await state.clear()
