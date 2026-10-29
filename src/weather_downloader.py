"""
Tải thời tiết lịch sử theo giờ cho danh sách sân bay.
Khoảng ngày: 2025-09-01 đến 2026-08-31 (bao gồm cả hai ngày).

Đầu vào:
  airports_to_fetch.csv
  - Có cột AIRPORT, hoặc ORIGIN và/hoặc DEST
  - Mã sân bay IATA, ví dụ JFK, LAX, SFO

Đầu ra:
  airport_weather_hourly.csv : thời tiết theo giờ, có AIRPORT, LATITUDE, LONGITUDE, TIME
  airport_coordinates.csv    : tọa độ tra được
  airports_not_found.csv     : mã không tra được tọa độ
  weather_download_errors.csv: sân bay tải lỗi (nếu có)

Cài thư viện:
  pip install pandas requests
"""

from pathlib import Path
import time
import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

# File danh sách sân bay đầu vào
AIRPORTS_FILE = BASE_DIR / "data" / "input" / "airports.txt"

# Thư mục lưu kết quả
OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Các file kết quả
OUTPUT_FILE = OUTPUT_DIR / "airport_weather_hourly.csv"
COORD_FILE = OUTPUT_DIR / "airport_coordinates.csv"
NOT_FOUND_FILE = OUTPUT_DIR / "airports_not_found.csv"
ERROR_FILE = OUTPUT_DIR / "weather_download_errors.csv"
START_DATE = "2025-09-01"
END_DATE = "2026-08-31"

AIRPORTS_URL = "https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "pressure_msl",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

def read_airport_codes(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Không thấy {path.name}. Hãy tạo airports.txt, mỗi dòng một mã sân bay "
            "ví dụ CID\\nABQ\\nSTL, rồi đặt cạnh file Python."
        )

    # File TXT: mỗi dòng một mã sân bay, ví dụ CID, ABQ, STL.
    # Bỏ qua dòng trống và loại mã trùng.
    codes = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            code = line.strip().upper()
            if code and code not in {"NAN", "NONE", "NULL"}:
                # Cho phép người dùng vô tình thêm dấu phẩy sau mã.
                code = code.split(",")[0].strip()
                if code:
                    codes.append(code)

    if not codes:
        raise ValueError("airports.txt đang trống hoặc không có mã sân bay hợp lệ.")

    return sorted(set(codes))

def get_airport_reference(session: requests.Session) -> pd.DataFrame:
    response = session.get(AIRPORTS_URL, timeout=60)
    response.raise_for_status()
    from io import BytesIO
    ref = pd.read_csv(BytesIO(response.content), dtype={"iata_code": str})
    ref = ref[
        ref["iata_code"].notna()
        & ref["latitude_deg"].notna()
        & ref["longitude_deg"].notna()
    ].copy()
    ref["iata_code"] = ref["iata_code"].astype(str).str.strip().str.upper()

    # Ưu tiên sân bay lớn/trung bình/nhỏ hơn các heliport/closed
    if "type" in ref.columns:
        priority = {"large_airport": 0, "medium_airport": 1, "small_airport": 2}
        ref["_priority"] = ref["type"].map(priority).fillna(9)
        ref = ref.sort_values(["_priority", "name"])
    ref = ref.drop_duplicates("iata_code", keep="first")
    return ref

def fetch_weather(session: requests.Session, code: str, lat: float, lon: float) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "auto",
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            response = session.get(WEATHER_URL, params=params, timeout=120)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(payload.get("reason", "API trả lỗi không rõ nguyên nhân"))

            hourly = payload.get("hourly")
            if not hourly or "time" not in hourly:
                raise RuntimeError("API không trả về dữ liệu hourly.")

            df = pd.DataFrame(hourly)
            df.insert(0, "AIRPORT", code)
            df.insert(1, "LATITUDE", lat)
            df.insert(2, "LONGITUDE", lon)
            # TIME là giờ địa phương của sân bay do timezone=auto.
            df.rename(columns={
                "time": "TIME",
                "temperature_2m": "TEMP_C",
                "relative_humidity_2m": "RELATIVE_HUMIDITY_PCT",
                "dew_point_2m": "DEW_POINT_C",
                "apparent_temperature": "APPARENT_TEMP_C",
                "precipitation": "PRECIPITATION_MM",
                "rain": "RAIN_MM",
                "snowfall": "SNOWFALL_CM",
                "weather_code": "WEATHER_CODE",
                "pressure_msl": "PRESSURE_MSL_HPA",
                "cloud_cover": "CLOUD_COVER_PCT",
                "wind_speed_10m": "WIND_SPEED_10M_KMH",
                "wind_direction_10m": "WIND_DIRECTION_10M_DEG",
                "wind_gusts_10m": "WIND_GUSTS_10M_KMH",
            }, inplace=True)
            return df
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                wait = attempt * 3
                print(f"  Lỗi lần {attempt}: {exc}. Thử lại sau {wait}s...")
                time.sleep(wait)
    raise RuntimeError(str(last_error))

def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "AirportWeatherDataset/1.0 (educational project)"})

    codes = read_airport_codes(AIRPORTS_FILE)
    print(f"Đã đọc {len(codes)} mã sân bay duy nhất từ airports.txt.")

    ref = get_airport_reference(session)
    coords = ref[ref["iata_code"].isin(codes)].copy()
    coords_out = coords[["iata_code", "name", "latitude_deg", "longitude_deg"]].rename(
        columns={
            "iata_code": "AIRPORT",
            "name": "AIRPORT_NAME",
            "latitude_deg": "LATITUDE",
            "longitude_deg": "LONGITUDE",
        }
    )
    coords_out.to_csv(COORD_FILE, index=False, encoding="utf-8-sig")

    found_codes = set(coords_out["AIRPORT"])
    missing = sorted(set(codes) - found_codes)
    pd.DataFrame({"AIRPORT": missing}).to_csv(
        NOT_FOUND_FILE, index=False, encoding="utf-8-sig"
    )
    print(f"Tra được tọa độ: {len(found_codes)}; không tra được: {len(missing)}.")
    if missing:
        print("Mã chưa tìm thấy:", ", ".join(missing[:30]))

    # Tải từng sân bay, nối các kết quả rồi ghi CSV.
    # Nếu chương trình bị ngắt, các sân bay đã hoàn tất vẫn được giữ trong file.
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    errors = []
    total = len(coords_out)
    for index, row in enumerate(coords_out.itertuples(index=False), start=1):
        code = row.AIRPORT
        lat = float(row.LATITUDE)
        lon = float(row.LONGITUDE)
        print(f"[{index}/{total}] Đang tải {code} ({lat}, {lon})...")

        try:
            weather = fetch_weather(session, code, lat, lon)
            weather.to_csv(
                OUTPUT_FILE,
                mode="a",
                header=not OUTPUT_FILE.exists(),
                index=False,
                encoding="utf-8-sig" if not OUTPUT_FILE.exists() else "utf-8",
            )
            print(f"  Đã lưu {len(weather):,} dòng.")
        except Exception as exc:
            print(f"  THẤT BẠI: {exc}")
            errors.append({"AIRPORT": code, "ERROR": str(exc)})

        # Nghỉ ngắn giữa các yêu cầu để tránh gửi quá dồn dập
        time.sleep(1)

    pd.DataFrame(errors, columns=["AIRPORT", "ERROR"]).to_csv(
        ERROR_FILE, index=False, encoding="utf-8-sig"
    )

    print("\nHoàn tất.")
    print(f"Thời tiết: {OUTPUT_FILE}")
    print(f"Tọa độ: {COORD_FILE}")
    print(f"Mã không tìm thấy: {NOT_FOUND_FILE}")
    print(f"Lỗi tải: {ERROR_FILE}")
    print("Lưu ý: TIME dùng giờ địa phương do API tự xác định múi giờ.")
    print("Khi mapping, hãy ghép theo AIRPORT + thời điểm đã chuẩn hóa múi giờ.")

if __name__ == "__main__":
    main()
