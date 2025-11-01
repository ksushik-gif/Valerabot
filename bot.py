import asyncio
from datetime import datetime
import logging
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv
from flask import Flask
import requests


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Получаем токены
TG_KEY = os.getenv("TG_KEY")
API_KEY = os.getenv("API_KEY")
PORT = int(os.getenv("PORT", 443))

if not TG_KEY:
    raise ValueError("Не найден TG_KEY в переменных окружения")
if not API_KEY:
    raise ValueError("Не найден API_KEY в переменных окружения")

# Инициализация бота и диспетчера
bot = Bot(token=TG_KEY, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Инициализация Flask приложения
app = Flask(__name__)

# Город по умолчанию
DEFAULT_CITY = "Saint Petersburg"


def get_weather(city: str) -> str:
    """Получает данные о погоде для указанного города"""
    try:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric",
            "lang": "ru",
        }

        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather", params=params
        )
        response.raise_for_status()
        data = response.json()

        weather_info = f"🌤 <b>Погода в {city}</b>\n\n"
        weather_info += (
            f"• <b>Состояние:</b> {data['weather'][0]['description'].capitalize()}\n"
        )
        weather_info += f"• <b>Температура:</b> {data['main']['temp']} °C\n"
        weather_info += f"• <b>Ощущается как:</b> {data['main']['feels_like']} °C\n"
        weather_info += f"• <b>Влажность:</b> {data['main']['humidity']}%\n"
        weather_info += f"• <b>Давление:</b> {data['main']['pressure']} гПа\n"
        weather_info += f"• <b>Скорость ветра:</b> {data['wind']['speed']} м/с\n"

        # Время заката
        sunset_timestamp = data["sys"]["sunset"]
        sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime("%H:%M:%S")
        weather_info += f"• <b>Закат:</b> {sunset_time}\n"

        return weather_info

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            return f"❌ Город '{city}' не найден. Проверьте правильность написания."
        else:
            return f"❌ Ошибка при получении данных: {e}"
    except Exception as e:
        return f"❌ Ошибка: {e}"


# Создаем клавиатуру
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌤 Погода в СПб"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="🏙 Сменить город")],
        ],
        resize_keyboard=True,
    )
    return keyboard


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 <b>Добро пожаловать в Weather Bot!</b>\n\n"
        "Я могу показать актуальную погоду в любом городе мира.\n\n"
        "<b>Доступные команды:</b>\n"
        "• /start - начать работу\n"
        "• /help - помощь\n"
        "• /weather <город> - погода в указанном городе\n"
        "• /city <город> - установить город по умолчанию\n\n"
        "<b>Быстрые кнопки:</b>\n"
        "• Погода в СПб - текущая погода\n"
        "• Сменить город - установить другой город"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())
    weather_info = get_weather(DEFAULT_CITY)
    await message.answer(weather_info)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📖 <b>Помощь по использованию бота</b>\n\n"
        "<b>Команды:</b>\n"
        "• /start - начать работу с ботом\n"
        "• /help - показать эту справку\n"
        "• /weather <город> - погода в указанном городе\n"
        "• /city <город> - установить город по умолчанию\n\n"
        "<b>Примеры:</b>\n"
        "<code>/weather Moscow</code> - погода в Москве\n"
        "<code>/city London</code> - установить Лондон городом по умолчанию"
    )
    await message.answer(help_text)


@dp.message(Command("weather"))
async def cmd_weather(message: types.Message):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.answer(
            "❌ Укажите город после команды.\n<b>Пример:</b> <code>/weather Moscow</code>"
        )
        return
    city = " ".join(command_parts[1:])
    await message.answer(f"🔍 Запрашиваю погоду для {city}...")
    weather_info = get_weather(city)
    await message.answer(weather_info)


@dp.message(Command("city"))
async def cmd_city(message: types.Message):
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.answer(
            "❌ Укажите город после команды.\n<b>Пример:</b> <code>/city London</code>"
        )
        return
    city = " ".join(command_parts[1:])
    weather_info = get_weather(city)
    if weather_info.startswith("❌"):
        await message.answer(weather_info)
    else:
        global DEFAULT_CITY
        DEFAULT_CITY = city
        await message.answer(
            f"✅ Город по умолчанию изменен на: <b>{city}</b>\n\n{weather_info}"
        )


@dp.message(F.text == "🌤 Погода в СПб")
async def weather_spb(message: types.Message):
    await message.answer("🔍 Запрашиваю погоду в Санкт-Петербурге...")
    weather_info = get_weather("Saint Petersburg")
    await message.answer(weather_info)


@dp.message(F.text == "❓ Помощь")
async def help_button(message: types.Message):
    await cmd_help(message)


@dp.message(F.text == "🏙 Сменить город")
async def change_city_button(message: types.Message):
    await message.answer(
        "🏙 Чтобы установить город по умолчанию, используйте команду:\n<code>/city &lt;город&gt;</code>"
    )


@dp.message(F.text)
async def handle_city_input(message: types.Message):
    text = message.text.strip()
    if text not in [
        "🌤 Погода в СПб",
        "❓ Помощь",
        "🏙 Сменить город",
    ] and not text.startswith("/"):
        await message.answer(f"🔍 Запрашиваю погоду для {text}...")
        weather_info = get_weather(text)
        await message.answer(weather_info)


# Flask маршруты
@app.route("/")
def home():
    return {"status": "Bot is running", "service": "Weather Telegram Bot"}


@app.route("/health")
def health():
    return {"status": "healthy"}


@app.route("/ping")
def ping():
    return "pong"


async def start_bot():
    """Запуск Telegram бота"""
    logger.info("Запуск Telegram бота...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


def run_bot():
    """Запуск бота в основном event loop"""
    asyncio.run(start_bot())


if __name__ == "__main__":
    # ЗАПУСКАЕМ БОТА В ОСНОВНОМ ПОТОКЕ, а Flask в отдельном
    from threading import Thread
    import time

    # Даем время на запуск
    time.sleep(2)

    # Запускаем Flask в отдельном потоке как демона
    flask_thread = Thread(
        target=lambda: app.run(
            host="0.0.0.0", port=PORT, debug=False, use_reloader=False
        )
    )
    flask_thread.daemon = True
    flask_thread.start()

    logger.info(f"Flask запущен на порту {PORT} в фоновом режиме")
    logger.info("Запускаем Telegram бота в основном потоке...")

    # Запускаем бота в основном потоке
    run_bot()
