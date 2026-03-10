import os
import json
import time
from openai import OpenAI
from sqlalchemy import select
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from bot.db import SessionLocal
from bot.models import Car

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")

def wait_for_token():
    print("TELEGRAM_BOT_TOKEN is not set or is a placeholder. Bot will idle.")
    while True:
        time.sleep(3600)

if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token":
    wait_for_token()

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

tools = [
    {
        "type": "function",
        "function": {
            "name": "extract_filters",
            "description": "Extract car filters from user query",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string"},
                    "model": {"type": "string"},
                    "year": {"type": "integer"},
                    "max_price": {"type": "integer"},
                    "color": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    }
]

def format_car(car: Car) -> str:
    return f"{car.brand} {car.model} {car.year} — {car.price} — {car.color}\n{car.url}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напишите запрос, например: Найди красную BMW до 2 млн")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not OPENAI_API_KEY:
        await update.message.reply_text("Нет доступа к LLM API. Укажите OPENAI_API_KEY.")
        return

    user_text = update.message.text
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You extract structured car filters from user queries."},
                {"role": "user", "content": user_text},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_filters"}},
        )

        tool_call = response.choices[0].message.tool_calls[0] if response.choices[0].message.tool_calls else None
        args = json.loads(tool_call.function.arguments) if tool_call else {}

        db = SessionLocal()
        try:
            stmt = select(Car)
            if args.get("brand"):
                stmt = stmt.where(Car.brand.ilike(f"%{args['brand']}%"))
            if args.get("model"):
                stmt = stmt.where(Car.model.ilike(f"%{args['model']}%"))
            if args.get("color"):
                stmt = stmt.where(Car.color.ilike(f"%{args['color']}%"))
            if args.get("year"):
                stmt = stmt.where(Car.year == args["year"])
            if args.get("max_price"):
                stmt = stmt.where(Car.price <= args["max_price"])

            stmt = stmt.order_by(Car.updated_at.desc())
            cars = db.execute(stmt).scalars().fetchmany(10)
        finally:
            db.close()

        if not cars:
            await update.message.reply_text("Не нашёл подходящих объявлений.")
            return

        text = "\n\n".join(format_car(car) for car in cars)
        await update.message.reply_text(text)
    except Exception:
        await update.message.reply_text("Ошибка обработки запроса.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
