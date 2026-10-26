
from pathlib import Path
import time
import requests
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "external" / "weather_2015"
OUT.mkdir(parents=True, exist_ok=True)

airports = pd.read_csv(RAW / "airports.csv")

airports.columns = airports.columns.str.upper()

airports = airports.dropna(
    subset=["IATA_CODE", "LATITUDE", "LONGITUDE"]
).drop_duplicates("IATA_CODE")

# Chia nhóm để tránh URL quá dài và phản hồi quá lớn
batch_size = 10
session = requests.Session()

for start in range(0, len(airports), batch_size):
    batch = airports.iloc[start:start + batch_size]

    codes = batch["IATA_CODE"].tolist()
    latitudes = batch["LATITUDE"].tolist()
    longitudes = batch["LONGITUDE"].tolist()

    params = {
        "latitude": ",".join(map(str, latitudes)),
        "longitude": ",".join(map(str, longitudes)),
        "start_date": "2015-01-01",
        "end_date": "2015-12-31",
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "snowfall",
            "weather_code",
            "visibility",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]),
        "timezone": "GMT",
        "wind_speed_unit": "kmh",
        "format": "csv",
    }

    path = OUT / (
        f"weather_{start:03d}_{start + len(batch) - 1:03d}.csv"
    )

    if path.exists():
        print("Da co, bo qua:", path.name)
        continue

    try:
        response = session.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params=params,
            timeout=300,
        )
        response.raise_for_status()

        content = response.content

        # Kiểm tra phản hồi có phải CSV hay trang lỗi
        if not content or b"<html" in content[:500].lower():
            raise ValueError("Phan hoi khong phai CSV hop le")

        path.write_bytes(content)
        print("Da tai:", path.name, codes)

    except Exception as exc:
        print("Loi voi nhom", codes, ":", exc)

    time.sleep(1)

print("Hoan tat cac nhom. Kiem tra cac file loi neu co.")
