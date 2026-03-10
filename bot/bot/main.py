import os
import json
import time
import re
from openai import OpenAI
from sqlalchemy import select
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from bot.db import SessionLocal
from bot.models import Car

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("VEDAI_API_KEY")
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

def normalize_filters(filters: dict) -> dict:
    brand_map = {
        "nissan": "日産",
        "ниссан": "日産",
        "daihatsu": "ダイハツ",
        "дайхатсу": "ダイハツ",
        "toyota": "トヨタ",
        "тойота": "トヨタ",
        "honda": "ホンダ",
        "хонда": "ホンダ",
        "mazda": "マツダ",
        "мазда": "マツダ",
        "suzuki": "スズキ",
        "сузуки": "スズキ",
        "mitsubishi": "三菱",
        "митсубиси": "三菱",
        "subaru": "スバル",
        "субару": "スバル",
        "lexus": "レクサス",
        "лексус": "レクサス",
        "bmw": "BMW",
        "audi": "Audi",
        "mercedes": "Mercedes",
    }
    color_map = {
        "black": "ブラック",
        "черн": "ブラック",
        "white": "ホワイト",
        "бел": "ホワイト",
        "red": "レッド",
        "красн": "レッド",
        "blue": "ブルー",
        "син": "ブルー",
        "green": "グリーン",
        "зел": "グリーン",
        "silver": "シルバー",
        "сер": "シルバー",
        "gray": "グレー",
        "grey": "グレー",
        "yellow": "イエロー",
        "желт": "イエロー",
        "orange": "オレンジ",
        "оранж": "オレンジ",
        "brown": "ブラウン",
        "коричн": "ブラウン",
        "beige": "ベージュ",
        "беж": "ベージュ",
    }
    if filters.get("brand"):
        key = str(filters["brand"]).strip().lower()
        filters["brand"] = brand_map.get(key, filters["brand"])
    if filters.get("color"):
        key = str(filters["color"]).strip().lower()
        for k, v in color_map.items():
            if key.startswith(k):
                filters["color"] = v
                break
    return filters

def fallback_extract(text: str) -> dict:
    result = {}
    color_match = re.search(r"(black|white|red|blue|green|gray|silver|yellow|orange|brown|beige|gold|pink|purple|черн|бел|красн|син|зел|сер|жёлт|желт|оранж|коричн|беж)", text, re.IGNORECASE)
    if color_match:
        result["color"] = color_match.group(1)
    price_match = re.search(r"до\s*([0-9]+(?:[\\s,.][0-9]+)?)\\s*(млн|миллион|тыс|тысяч)?", text, re.IGNORECASE)
    if price_match:
        value = price_match.group(1).replace(" ", "").replace(",", ".")
        try:
            num = float(value)
            unit = price_match.group(2) or ""
            if "млн" in unit or "мил" in unit:
                result["max_price"] = int(num * 1_000_000)
            elif "тыс" in unit:
                result["max_price"] = int(num * 1_000)
            else:
                result["max_price"] = int(num)
        except Exception:
            pass
    brand_match = re.search(r"\b(BMW|Audi|Toyota|Nissan|Lexus|Mercedes|Kia|Hyundai|Volkswagen|Skoda|Mazda|Honda|Ford|Chevrolet|Jeep|Subaru|Volvo|Porsche|Daihatsu|Suzuki|Mitsubishi|Infiniti|Ниссан|Дайхатсу|Тойота|Хонда|Мазда|Сузуки|Митсубиси|Субару|Лексус)\b", text, re.IGNORECASE)
    if brand_match:
        result["brand"] = brand_match.group(1)
    return normalize_filters(result)

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
        if not args:
            args = fallback_extract(user_text)
        else:
            args = normalize_filters(args)

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
    except Exception as err:
        print(f"LLM error: {err}", flush=True)
        args = fallback_extract(user_text)
        if not args:
            await update.message.reply_text("Ошибка обработки запроса.")
            return
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

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
