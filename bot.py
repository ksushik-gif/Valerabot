from datetime import datetime
import os

from dotenv import load_dotenv
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,  # Добавлено: необходим для обработки callback_query
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# Загружаем переменные из .env
load_dotenv()

# Получаем ключи из переменных окружения
TG_KEY = os.getenv("TG_KEY")
API_KEY = os.getenv("API_KEY")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Saint Petersburg")

if not TG_KEY:
    raise ValueError("Не найден TG_KEY в .env")
if not API_KEY:
    raise ValueError("Не найден API_KEY в .env")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [
            InlineKeyboardButton(
                "Погода в стандартном городе", callback_data=f"city:{DEFAULT_CITY}"
            )
        ],
        [InlineKeyboardButton("Указать другой город", callback_data="input_city")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Привет! Я бот для просмотра погоды.\n"
        f"Стандартный город: {DEFAULT_CITY}.\n"
        "Выберите действие:",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "Команды бота:\n"
        "/start — начать работу, выбрать город\n"
        "/help — показать эту справку\n\n"
        "Чтобы узнать погоду в конкретном городе, просто напишите его название."
    )
    await update.message.reply_text(help_text)


def get_weather(city: str) -> str:
    """Получает погоду для города и формирует текст ответа"""
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "ru",
    }

    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather", params=params
        )
        r.raise_for_status()
        data = r.json()

        weather = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        pressure = data["main"].get("grnd_level", "н/д")
        wind = data["wind"]["speed"]
        sunset_timestamp = data["sys"]["sunset"]
        sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime("%H:%M")

        return (
            f"Погода в {city}:\n"
            f"→ {weather}\n"
            f"→ Температура: {temp} °C\n"
            f"→ Влажность: {humidity} %\n"
            f"→ Давление: {pressure} гПа\n"
            f"→ Ветер: {wind} м/с\n"
            f"→ Закат: {sunset_time}"
        )

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Город «{city}» не найден."
        else:
            return f"Ошибка API: {e}"
    except Exception as e:
        return f"Произошла ошибка: {e}"


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("city:"):
        city = query.data.split("city:")[1]
        weather_info = get_weather(city)
        await query.edit_message_text(text=weather_info)

    elif query.data == "input_city":
        await query.edit_message_text(text="Введите название города:")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (название города)"""
    city = update.message.text.strip()
    weather_info = get_weather(city)
    await update.message.reply_text(weather_info)


def main():
    """Основная функция запуска бота"""
    application = Application.builder().token(TG_KEY).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )
    # Исправлено: используем CallbackQueryHandler вместо некорректного вызова
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен. Ожидание сообщений...")
    application.run_polling()


if __name__ == "__main__":
    main()
