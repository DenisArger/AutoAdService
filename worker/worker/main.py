import os
import re
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from worker.db import SessionLocal
from worker.models import Car

BASE_URL = os.environ.get("CARSENSOR_URL", "https://www.carsensor.net")
LIST_URL = os.environ.get("CARSENSOR_LIST_URL", f"{BASE_URL}/usedcar/index.html")
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
            res.encoding = res.apparent_encoding
            return res.text
        except Exception as err:
            last_err = err
            time.sleep(2 ** i)
    raise last_err

def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def extract_detail_links(html: str):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.select('a[href*="/usedcar/detail/"]'):
        href = a.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = f"{BASE_URL}{href}"
        if "carsensor.net/usedcar/detail/" in href:
            links.add(href.split("?")[0])
    return list(links)

def parse_car_detail(html: str, url: str):
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if not h1:
        return None
    title = normalize_text(h1.get_text(" "))

    color = "unknown"
    color_match = re.search(r"[（(]([^）)]+)[）)]", title)
    if color_match:
        color = color_match.group(1)

    title_no_color = re.sub(r"[（(].*?[）)]", "", title).strip()
    parts = title_no_color.split()
    if len(parts) < 2:
        return None
    brand = parts[0]
    model = parts[1]

    text = normalize_text(soup.get_text(" "))
    year_match = re.search(r"年式\s*([0-9]{4})", text)
    if not year_match:
        return None
    year = int(year_match.group(1))

    price_match = re.search(r"車両本体価格.*?([0-9]+(?:\.[0-9])?)\s*万円", text)
    if not price_match:
        price_match = re.search(r"本体価格\s*([0-9]+(?:\.[0-9])?)\s*万円", text)
    if not price_match:
        return None
    price = int(float(price_match.group(1)) * 10000)

    return {"brand": brand, "model": model, "year": year, "price": price, "color": color, "url": url}

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
        links = extract_detail_links(html)
        cars = []
        for link in links[:20]:
            detail_html = fetch_with_retry(link, 3)
            car = parse_car_detail(detail_html, link)
            if car:
                cars.append(car)
        if not cars:
            print("No cars parsed. Check selectors for carsensor.net", flush=True)
            return
        db = SessionLocal()
        try:
            for car in cars:
                upsert_car(db, car)
        finally:
            db.close()
        print(f"Scraped and upserted {len(cars)} cars", flush=True)
    except Exception as err:
        print(f"Scrape failed: {err}", flush=True)

def main():
    interval = sleep_seconds()
    print(f"Worker started. Interval: {interval}s", flush=True)
    while True:
        scrape_once()
        time.sleep(interval)

if __name__ == "__main__":
    main()
