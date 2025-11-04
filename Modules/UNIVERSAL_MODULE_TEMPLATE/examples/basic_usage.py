"""
Примеры базового использования универсального шаблона модуля

Этот файл содержит простые примеры того, как использовать
компоненты шаблона для создания собственных модулей.
"""

# === ПРИМЕР 1: СОЗДАНИЕ ПРОСТОГО ОБРАБОТЧИКА КОМАНДЫ ===

from aiogram import Router, types
from aiogram.filters import Command
from loguru import logger

# Создаем роутер
my_router = Router(name="my_module")

@my_router.message(Command("my_command"))
async def my_command_handler(message: types.Message):
    """
    Простой обработчик команды
    
    Этот пример показывает, как создать базовый обработчик команды.
    """
    await message.answer(
        "🔧 **Моя команда**\n\n"
        "Это пример простой команды модуля."
    )

# === ПРИМЕР 2: ИСПОЛЬЗОВАНИЕ РАЗРЕШЕНИЙ ===

from .utils import check_permission
from .permissions import PERMISSIONS

@my_router.message(Command("protected_command"))
async def protected_command_handler(message: types.Message, services):
    """
    Обработчик команды с проверкой разрешений
    
    Этот пример показывает, как проверить разрешения пользователя.
    """
    # Проверяем разрешение
    if not await check_permission(services, message.from_user.id, PERMISSIONS.ACCESS):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
    
    await message.answer(
        "🔐 **Защищенная команда**\n\n"
        "У вас есть доступ к этой команде!"
    )

# === ПРИМЕР 3: РАБОТА С БАЗОЙ ДАННЫХ ===

from .services import TemplateService

@my_router.message(Command("create_item"))
async def create_item_handler(message: types.Message, services):
    """
    Создание элемента через сервис
    
    Этот пример показывает, как использовать сервис для работы с БД.
    """
    # Получаем настройки модуля
    settings = services.modules.get_module_settings("my_module") or {}
    
    # Создаем сервис
    template_service = TemplateService(services, settings)
    
    # Создаем элемент
    new_item = await template_service.create_item(
        user_id=message.from_user.id,
        title="Пример элемента",
        description="Создан через команду",
        priority=50
    )
    
    if new_item:
        await message.answer(
            f"✅ **Элемент создан!**\n\n"
            f"**ID:** {new_item.id}\n"
            f"**Заголовок:** {new_item.title}"
        )
    else:
        await message.answer("❌ Не удалось создать элемент")

# === ПРИМЕР 4: ИСПОЛЬЗОВАНИЕ КЛАВИАТУР ===

from .keyboards import get_main_menu_keyboard, get_simple_back_keyboard

@my_router.message(Command("menu"))
async def menu_handler(message: types.Message):
    """
    Показ меню с клавиатурой
    
    Этот пример показывает, как использовать готовые клавиатуры.
    """
    keyboard = get_main_menu_keyboard()
    await message.answer(
        "🔧 **Главное меню**\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# === ПРИМЕР 5: ОБРАБОТКА CALLBACK ЗАПРОСОВ ===

from .callback_data_factories import TemplateCallback, parse_template_callback

@my_router.callback_query(TemplateCallback.filter())
async def callback_handler(callback: types.CallbackQuery):
    """
    Обработчик callback запросов
    
    Этот пример показывает, как обрабатывать нажатия на inline кнопки.
    """
    # Парсим callback data
    callback_data = parse_template_callback(callback.data)
    
    if not callback_data:
        await callback.answer("❌ Ошибка обработки запроса")
        return
    
    # Обрабатываем разные действия
    if callback_data.action == "show_info":
        await callback.message.edit_text(
            "ℹ️ **Информация**\n\n"
            "Это пример обработки callback запроса."
        )
    elif callback_data.action == "show_back":
        keyboard = get_simple_back_keyboard()
        await callback.message.edit_text(
            "🔙 **Назад**\n\n"
            "Вы вернулись назад.",
            reply_markup=keyboard
        )
    
    await callback.answer()

# === ПРИМЕР 6: FSM ДИАЛОГ ===

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

class MyStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()

@my_router.message(Command("dialog"))
async def start_dialog(message: types.Message, state: FSMContext):
    """
    Начало FSM диалога
    
    Этот пример показывает, как создать простой диалог с пользователем.
    """
    await state.set_state(MyStates.waiting_name)
    await message.answer(
        "🗣️ **Диалог**\n\n"
        "Шаг 1: Как вас зовут?\n\n"
        "Отправьте ваше имя:"
    )

@my_router.message(StateFilter(MyStates.waiting_name))
async def process_name(message: types.Message, state: FSMContext):
    """
    Обработка ввода имени
    """
    # Сохраняем имя
    await state.update_data(name=message.text)
    
    # Переходим к следующему шагу
    await state.set_state(MyStates.waiting_age)
    await message.answer(
        f"✅ Приятно познакомиться, {message.text}!\n\n"
        "Шаг 2: Сколько вам лет?\n\n"
        "Отправьте ваш возраст:"
    )

@my_router.message(StateFilter(MyStates.waiting_age))
async def process_age(message: types.Message, state: FSMContext):
    """
    Обработка ввода возраста и завершение диалога
    """
    try:
        age = int(message.text)
        if age < 0 or age > 150:
            await message.answer("❌ Введите корректный возраст (0-150)")
            return
    except ValueError:
        await message.answer("❌ Введите число")
        return
    
    # Получаем все данные
    data = await state.get_data()
    
    await message.answer(
        f"✅ **Диалог завершен!**\n\n"
        f"**Имя:** {data['name']}\n"
        f"**Возраст:** {age} лет\n\n"
        "Спасибо за участие в диалоге!"
    )
    
    # Очищаем состояние
    await state.clear()

# === ПРИМЕР 7: ОБРАБОТКА ОШИБОК ===

@my_router.message(Command("error_example"))
async def error_example_handler(message: types.Message):
    """
    Пример обработки ошибок
    
    Этот пример показывает, как правильно обрабатывать ошибки.
    """
    try:
        # Имитируем операцию, которая может вызвать ошибку
        result = 10 / 0  # Это вызовет ZeroDivisionError
        
    except ZeroDivisionError:
        logger.error("Деление на ноль в error_example_handler")
        await message.answer("❌ Произошла ошибка: деление на ноль")
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка в error_example_handler: {e}")
        await message.answer("❌ Произошла неожиданная ошибка")
        
    else:
        # Этот блок выполнится, если ошибок не было
        await message.answer(f"✅ Результат: {result}")

# === ПРИМЕР 8: ЛОГИРОВАНИЕ ДЕЙСТВИЙ ===

from .utils import log_module_action

@my_router.message(Command("log_example"))
async def log_example_handler(message: types.Message, services):
    """
    Пример логирования действий
    
    Этот пример показывает, как логировать действия пользователей.
    """
    # Логируем начало действия
    log_module_action(
        services,
        "log_example_command",
        message.from_user.id,
        {"command": "/log_example"}
    )
    
    await message.answer(
        "📝 **Пример логирования**\n\n"
        "Это действие было залогировано в аудит системы."
    )

# === ПРИМЕР 9: ВАЛИДАЦИЯ ДАННЫХ ===

from .utils import validate_input, validate_email

@my_router.message(Command("validate_example"))
async def validate_example_handler(message: types.Message):
    """
    Пример валидации данных
    
    Этот пример показывает, как валидировать пользовательский ввод.
    """
    # Получаем аргументы команды
    args = message.text.split()[1:]  # Убираем саму команду
    
    if len(args) < 2:
        await message.answer(
            "❌ **Неверное использование команды**\n\n"
            "Использование: /validate_example <текст> <email>\n\n"
            "Пример: /validate_example 'Привет мир' user@example.com"
        )
        return
    
    text = args[0]
    email = args[1]
    
    # Валидируем текст
    if not validate_input(text, min_length=1, max_length=100):
        await message.answer("❌ Текст должен содержать от 1 до 100 символов")
        return
    
    # Валидируем email
    if not validate_email(email):
        await message.answer("❌ Некорректный email адрес")
        return
    
    await message.answer(
        f"✅ **Валидация прошла успешно!**\n\n"
        f"**Текст:** {text}\n"
        f"**Email:** {email}"
    )

# === ПРИМЕР 10: РАБОТА С НАСТРОЙКАМИ ===

@my_router.message(Command("settings_example"))
async def settings_example_handler(message: types.Message, services):
    """
    Пример работы с настройками модуля
    
    Этот пример показывает, как получить и использовать настройки.
    """
    # Получаем настройки модуля
    settings = services.modules.get_module_settings("my_module") or {}
    
    # Используем настройки
    max_items = settings.get('max_items_per_user', 10)
    debug_mode = settings.get('debug_mode', False)
    api_key = settings.get('api_key', '')
    
    await message.answer(
        f"⚙️ **Настройки модуля**\n\n"
        f"**Максимум элементов:** {max_items}\n"
        f"**Режим отладки:** {'✅ Включен' if debug_mode else '❌ Выключен'}\n"
        f"**API ключ:** {'✅ Установлен' if api_key else '❌ Не установлен'}"
    )
