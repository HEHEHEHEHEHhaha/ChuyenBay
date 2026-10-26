
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

files = {
    "flights.parquet":
        "https://huggingface.co/datasets/hsanchezp/us-dot-flight-delays-2015/resolve/main/flights.parquet",
    "airlines.parquet":
        "https://huggingface.co/datasets/hsanchezp/us-dot-flight-delays-2015/resolve/main/airlines.parquet",
    "airports.parquet":
        "https://huggingface.co/datasets/hsanchezp/us-dot-flight-delays-2015/resolve/main/airports.parquet",
}

for filename, url in files.items():
    destination = RAW / filename

    if destination.exists():
        print(f"Da co, bo qua: {filename}")
        continue

    print(f"Dang tai: {filename}")

    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()

        with destination.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(f"Da luu: {destination}")

print("Hoan tat tai du lieu.")
