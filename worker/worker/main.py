import os
import re
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from worker.db import SessionLocal
from worker.models import Car

BASE_URL = os.environ.get("CARSENSOR_URL", "https://carsensor.net")
LIST_URL = os.environ.get("CARSENSOR_LIST_URL", f"{BASE_URL}/cars")
CRON = os.environ.get("WORKER_CRON", "*/15 * * * *")

COLOR_PATTERN = re.compile(
    r"(black|white|red|blue|green|gray|silver|yellow|orange|brown|beige|gold|pink|purple|"
    r"серый|черный|чёрный|белый|красный|синий|зелёный|зеленый|желтый|жёлтый|оранжевый|"
    r"коричневый|бежевый)",
    re.IGNORECASE,
)

def parse_interval_minutes(cron_expr: str) -> int:
    if cron_expr.startswith("*/"):
        try:
            return int(cron_expr.split("*/")[1].split(" ")[0])
        except Exception:
            return 15
    return 15

def sleep_seconds():
    return parse_interval_minutes(CRON) * 60

def fetch_with_retry(url: str, attempts: int = 3):
    last_err = None
    for i in range(attempts):
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            return res.text
        except Exception as err:
            last_err = err
            time.sleep(2 ** i)
    raise last_err

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def parse_cars(html: str):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    candidates = soup.select(".car-item, .listing-item, article, .listing, .item")
    blocks = candidates if candidates else soup.find_all("a")

    for el in blocks:
        url = None
        link = el if el.name == "a" else el.find("a")
        if link and link.get("href"):
            url = link.get("href")
        if not url or url.startswith("javascript:"):
            continue
        if url.startswith("/"):
            url = f"{BASE_URL}{url}"

        text = normalize_text(el.get_text(" "))
        brand_model = re.search(r"([A-Za-zА-Яа-я]+)\s+([A-Za-zА-Яа-я0-9-]+)", text)
        year_match = re.search(r"(19\d{2}|20\d{2})", text)
        price_match = re.search(r"(\d{3,9})", text.replace(" ", ""))
        color_match = COLOR_PATTERN.search(text)

        if not brand_model or not year_match or not price_match:
            continue

        brand = brand_model.group(1)
        model = brand_model.group(2)
        year = int(year_match.group(1))
        price = int(price_match.group(1))
        color = color_match.group(1) if color_match else "unknown"

        items.append(
            {"brand": brand, "model": model, "year": year, "price": price, "color": color, "url": url}
        )

    return items

def upsert_car(db, car):
    existing = db.execute(select(Car).where(Car.url == car["url"])).scalar_one_or_none()
    if existing:
        existing.brand = car["brand"]
        existing.model = car["model"]
        existing.year = car["year"]
        existing.price = car["price"]
        existing.color = car["color"]
    else:
        db.add(Car(**car))
    db.commit()

def scrape_once():
    try:
        html = fetch_with_retry(LIST_URL, 3)
        cars = parse_cars(html)
        if not cars:
            print("No cars parsed. Check selectors for carsensor.net")
            return
        db = SessionLocal()
        try:
            for car in cars:
                upsert_car(db, car)
        finally:
            db.close()
        print(f"Scraped and upserted {len(cars)} cars")
    except Exception as err:
        print(f"Scrape failed: {err}")

def main():
    interval = sleep_seconds()
    print(f"Worker started. Interval: {interval}s")
    while True:
        scrape_once()
        time.sleep(interval)

if __name__ == "__main__":
    main()
