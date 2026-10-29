from pathlib import Path
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import numpy as np

try:
    from timezonefinder import TimezoneFinder
except ImportError:
    raise ImportError(
        "Thieu timezonefinder. Hay chay: pip install timezonefinder"
    )


# ============================================================
# 1. CAU HINH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FLIGHT_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "output"

WEATHER_FILE = OUTPUT_DIR / "airport_weather_hourly.csv"

MAX_WEATHER_AGE_MINUTES = 90
CHUNK_SIZE = 100_000

WEATHER_COLUMNS = [
    "TEMP_C",
    "RELATIVE_HUMIDITY_PCT",
    "DEW_POINT_C",
    "APPARENT_TEMP_C",
    "PRECIPITATION_MM",
    "RAIN_MM",
    "SNOWFALL_CM",
    "WEATHER_CODE",
    "PRESSURE_MSL_HPA",
    "CLOUD_COVER_PCT",
    "WIND_SPEED_10M_KMH",
    "WIND_DIRECTION_10M_DEG",
    "WIND_GUSTS_10M_KMH",
]

OUTPUT_WEATHER_COLUMNS = [
    f"{side}_{col}"
    for side in ["ORIGIN", "DEST"]
    for col in WEATHER_COLUMNS
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

tf = TimezoneFinder()


# ============================================================
# 2. CHUAN HOA DU LIEU
# ============================================================

def normalize_airport(value):
    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    if value in {"", "NAN", "NONE", "NULL"}:
        return ""

    if value.endswith(".0"):
        value = value[:-2]

    return value


def parse_flight_date(series):
    """
    BTS co the dung dang:
    12/4/2025 12:00:00 AM
    12/04/2025
    2025-12-04

    Thu tu uu tien thang/ngay/nam cho dinh dang co dau /.
    """
    text = series.astype("string").str.strip()

    result = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]",
    )

    formats = [
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        missing = result.isna()

        if not missing.any():
            break

        result.loc[missing] = pd.to_datetime(
            text.loc[missing],
            format=fmt,
            errors="coerce",
        )

    return result


def parse_hhmm(value):
    """
    Chuyen gio BTS thanh (hour, minute).

    635  -> (6, 35)
    1955 -> (19, 55)
    2400 -> (0, 0), ngay tiep theo
    """
    if pd.isna(value):
        return None

    try:
        number = float(value)
    except (ValueError, TypeError):
        return None

    if not np.isfinite(number) or number != int(number):
        return None

    number = int(number)

    if number == 2400:
        return (24, 0)

    if number < 0 or number > 2359:
        return None

    hour = number // 100
    minute = number % 100

    if hour > 23 or minute > 59:
        return None

    return (hour, minute)


def local_datetime(flight_date, hhmm):
    """Tao datetime dia phuong tu ngay bay va gio HHMM."""
    if pd.isna(flight_date):
        return pd.NaT

    parsed_time = parse_hhmm(hhmm)

    if parsed_time is None:
        return pd.NaT

    hour, minute = parsed_time

    base_date = pd.Timestamp(flight_date).normalize()

    if hour == 24:
        return base_date + pd.Timedelta(days=1)

    return base_date + pd.Timedelta(
        hours=hour,
        minutes=minute,
    )


# ============================================================
# 3. DOC VA CHUAN BI THOI TIET
# ============================================================

def load_all_weather():
    if not WEATHER_FILE.exists():
        raise FileNotFoundError(
            f"Khong tim thay file thoi tiet: {WEATHER_FILE}"
        )

    frames = []

    for chunk in pd.read_csv(
        WEATHER_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ):
        required = {
            "AIRPORT",
            "LATITUDE",
            "LONGITUDE",
            "TIME",
        }

        missing = required - set(chunk.columns)

        if missing:
            raise ValueError(
                f"File thoi tiet thieu cot: {sorted(missing)}"
            )

        chunk["AIRPORT"] = chunk["AIRPORT"].map(
            normalize_airport
        )

        chunk["TIME"] = pd.to_datetime(
            chunk["TIME"],
            errors="coerce",
        )

        chunk = chunk.dropna(
            subset=["AIRPORT", "TIME"]
        ).copy()

        chunk = chunk[chunk["AIRPORT"] != ""]

        for col in WEATHER_COLUMNS:
            if col not in chunk.columns:
                chunk[col] = np.nan

        # Chi giu cot can thiet de tiet kiem bo nho.
        frames.append(
            chunk[
                [
                    "AIRPORT",
                    "LATITUDE",
                    "LONGITUDE",
                    "TIME",
                ] + WEATHER_COLUMNS
            ]
        )

    if not frames:
        raise ValueError("File thoi tiet khong co ban ghi hop le.")

    weather = pd.concat(frames, ignore_index=True)

    weather = weather.drop_duplicates(
        subset=["AIRPORT", "TIME"],
        keep="last",
    )

    weather = weather.sort_values(
        ["AIRPORT", "TIME"]
    ).reset_index(drop=True)

    print("So ban ghi thoi tiet:", f"{len(weather):,}")
    print(
        "So san bay co thoi tiet:",
        weather["AIRPORT"].nunique(),
    )
    print(
        "Khoang thoi gian thoi tiet:",
        weather["TIME"].min(),
        "->",
        weather["TIME"].max(),
    )

    return weather


# ============================================================
# 4. XAC DINH MUI GIO SAN BAY
# ============================================================

def build_airport_info(weather):
    """
    Lay toa do va mui gio cua tung san bay.

    Luu y: timezonefinder can toa do hop le.
    """
    info = {}

    unique_airports = weather[
        ["AIRPORT", "LATITUDE", "LONGITUDE"]
    ].drop_duplicates("AIRPORT")

    for row in unique_airports.itertuples(index=False):
        airport = row.AIRPORT

        try:
            lat = float(row.LATITUDE)
            lon = float(row.LONGITUDE)

            if not np.isfinite(lat) or not np.isfinite(lon):
                raise ValueError("Toa do khong hop le")

            timezone = tf.timezone_at(
                lat=lat,
                lng=lon,
            )

        except (ValueError, TypeError):
            timezone = None

        info[airport] = {
            "timezone": timezone,
        }

    return info


# ============================================================
# 5. TINH THOI DIEM DEN THEO GIO DIA PHUONG
# ============================================================

def get_destination_datetime(
    flight_date,
    departure_hhmm,
    arrival_hhmm,
    elapsed_minutes,
    origin_timezone,
    destination_timezone,
):
    """
    1. Tao gio khoi hanh theo lich tai san bay di.
    2. Gan mui gio san bay di.
    3. Chuyen sang UTC.
    4. Cong CRS_ELAPSED_TIME.
    5. Chuyen sang mui gio san bay den de lay ngay den.
    6. Dung CRS_ARR_TIME lam gio den theo lich.

    Neu khong du thong tin de suy ra ngay den, tra ve NaT.
    """
    departure = local_datetime(
        flight_date,
        departure_hhmm,
    )

    arrival_clock = parse_hhmm(arrival_hhmm)

    if pd.isna(departure) or arrival_clock is None:
        return pd.NaT

    if pd.isna(elapsed_minutes):
        return pd.NaT

    try:
        elapsed_minutes = float(elapsed_minutes)

        if (
            not np.isfinite(elapsed_minutes)
            or elapsed_minutes <= 0
        ):
            return pd.NaT

        origin_tz = ZoneInfo(origin_timezone)
        destination_tz = ZoneInfo(destination_timezone)

        departure_aware = departure.to_pydatetime().replace(
            tzinfo=origin_tz
        )

        departure_utc = pd.Timestamp(
            departure_aware
        ).tz_convert("UTC")

        arrival_utc = departure_utc + pd.Timedelta(
            minutes=elapsed_minutes
        )

        arrival_local = arrival_utc.tz_convert(
            destination_tz
        )

        # Ngay den duoc suy ra tu thoi gian bay va mui gio.
        arrival_date = arrival_local.date()

        hour, minute = arrival_clock

        if hour == 24:
            arrival_date = (
                pd.Timestamp(arrival_date)
                + pd.Timedelta(days=1)
            ).date()

            hour = 0

        return pd.Timestamp(
            year=arrival_date.year,
            month=arrival_date.month,
            day=arrival_date.day,
            hour=hour,
            minute=minute,
        )

    except (
        ValueError,
        TypeError,
        ZoneInfoNotFoundError,
        OverflowError,
    ):
        return pd.NaT


# ============================================================
# 6. GHEP THOI TIET CHO MOT SAN BAY
# ============================================================

def map_weather_side(
    flights,
    weather,
    airport_info,
    airport_column,
    target_column,
    prefix,
):
    """
    Ghep moc thoi tiet gan nhat truoc thoi diem muc tieu,
    khong qua 90 phut.

    Khong ghep theo ten san bay don thuan.
    Bat buoc trung san bay va dung moc thoi gian hop le.
    """
    output = pd.DataFrame(
        np.nan,
        index=flights.index,
        columns=[f"{prefix}_{c}" for c in WEATHER_COLUMNS],
    )

    airports = flights[airport_column].map(
        normalize_airport
    )

    target_times = flights[target_column]

    # Xu ly tung san bay, tranh ghep nham thoi tiet cua san bay khac.
    for airport in airports.unique():
        if not airport:
            continue

        mask = (
            airports.eq(airport)
            & target_times.notna()
        )

        if not mask.any():
            continue

        airport_weather = weather[
            weather["AIRPORT"].eq(airport)
        ].copy()

        if airport_weather.empty:
            continue

        left = pd.DataFrame({
            "_row_index": flights.index[mask],
            "_target_time": pd.to_datetime(
                target_times.loc[mask],
                errors="coerce",
            ).values,
        })

        right = airport_weather[
            ["TIME"] + WEATHER_COLUMNS
        ].rename(
            columns={"TIME": "_weather_time"}
        )

        left["_target_time"] = pd.to_datetime(
            left["_target_time"],
            errors="coerce",
        ).astype("datetime64[ns]")

        right["_weather_time"] = pd.to_datetime(
            right["_weather_time"],
            errors="coerce",
        ).astype("datetime64[ns]")

        left = (
            left.dropna(subset=["_target_time"])
            .sort_values("_target_time")
        )

        right = (
            right.dropna(subset=["_weather_time"])
            .sort_values("_weather_time")
        )

        if left.empty or right.empty:
            continue

        merged = pd.merge_asof(
            left,
            right,
            left_on="_target_time",
            right_on="_weather_time",
            direction="backward",
            tolerance=pd.Timedelta(
                minutes=MAX_WEATHER_AGE_MINUTES
            ),
        )

        merged = merged.set_index("_row_index")

        for col in WEATHER_COLUMNS:
            output.loc[
                merged.index,
                f"{prefix}_{col}",
            ] = merged[col].to_numpy()

    return output


# ============================================================
# 7. XU LY MOT FILE CHUYEN BAY
# ============================================================

def process_flight_file(
    input_file,
    weather,
    airport_info,
):
    print(f"\nDang xu ly: {input_file.name}")

    flights = pd.read_csv(
        input_file,
        low_memory=False,
    )

    if flights.empty:
        print("File rong, bo qua.")
        return

    required = [
        "FL_DATE",
        "ORIGIN",
        "DEST",
        "CRS_DEP_TIME",
        "CRS_ARR_TIME",
        "CRS_ELAPSED_TIME",
    ]

    missing = [
        col for col in required
        if col not in flights.columns
    ]

    if missing:
        print("Thieu cot bat buoc:", missing)
        return

    # Xoa cot mapping cu de tranh _x va _y.
    flights = flights.drop(
        columns=[
            col for col in OUTPUT_WEATHER_COLUMNS
            if col in flights.columns
        ],
        errors="ignore",
    )

    # Dung index moi, lien tuc de tranh loi gan du lieu.
    flights = flights.reset_index(drop=True)

    # Doc FL_DATE theo dung format BTS.
    flights["_FLIGHT_DATE"] = parse_flight_date(
        flights["FL_DATE"]
    )

    flights["ORIGIN"] = flights["ORIGIN"].map(
        normalize_airport
    )

    flights["DEST"] = flights["DEST"].map(
        normalize_airport
    )

    flights["CRS_ELAPSED_TIME"] = pd.to_numeric(
        flights["CRS_ELAPSED_TIME"],
        errors="coerce",
    )

    # Gio khoi hanh dia phuong tai san bay di.
    flights["_ORIGIN_TARGET"] = [
        local_datetime(date, time)
        for date, time in zip(
            flights["_FLIGHT_DATE"],
            flights["CRS_DEP_TIME"],
        )
    ]

    # Tinh ngay den theo lich, co tinh den mui gio va thoi gian bay.
    destination_times = []

    for row in flights.itertuples(index=False):
        # Dung ten cot de lay gia tri, khong dua vao vi tri cot.
        destination_times.append(None)

    # Tao bang tam de truy cap cac cot bat buoc.
    for i in flights.index:
        origin = flights.at[i, "ORIGIN"]
        destination = flights.at[i, "DEST"]

        origin_tz = airport_info.get(
            origin, {}
        ).get("timezone")

        destination_tz = airport_info.get(
            destination, {}
        ).get("timezone")

        if not origin_tz or not destination_tz:
            destination_times.append(pd.NaT)
            continue

        target = get_destination_datetime(
            flight_date=flights.at[i, "_FLIGHT_DATE"],
            departure_hhmm=flights.at[i, "CRS_DEP_TIME"],
            arrival_hhmm=flights.at[i, "CRS_ARR_TIME"],
            elapsed_minutes=flights.at[i, "CRS_ELAPSED_TIME"],
            origin_timezone=origin_tz,
            destination_timezone=destination_tz,
        )

        destination_times.append(target)

    # Bo danh sach None ban dau, giu cac ket qua tinh duoc.
    destination_times = destination_times[len(flights):]

    flights["_DEST_TARGET"] = pd.to_datetime(
        destination_times,
        errors="coerce",
    )

    origin_weather = map_weather_side(
        flights=flights,
        weather=weather,
        airport_info=airport_info,
        airport_column="ORIGIN",
        target_column="_ORIGIN_TARGET",
        prefix="ORIGIN",
    )

    destination_weather = map_weather_side(
        flights=flights,
        weather=weather,
        airport_info=airport_info,
        airport_column="DEST",
        target_column="_DEST_TARGET",
        prefix="DEST",
    )

    result = pd.concat(
        [
            flights.drop(
                columns=[
                    "_FLIGHT_DATE",
                    "_ORIGIN_TARGET",
                    "_DEST_TARGET",
                ]
            ),
            origin_weather,
            destination_weather,
        ],
        axis=1,
    )

    output_file = (
        OUTPUT_DIR
        / f"{input_file.stem}_weather_mapped.csv"
    )

    result.to_csv(
        output_file,
        index=False,
    )

    total = len(result)

    origin_matched = result[
        "ORIGIN_TEMP_C"
    ].notna().sum()

    destination_matched = result[
        "DEST_TEMP_C"
    ].notna().sum()

    print("Da ghi:", output_file)
    print("So dong:", f"{total:,}")
    print(
        f"Thoi tiet san bay di: {origin_matched:,}/{total:,}"
    )
    print(
        f"Thoi tiet san bay den: {destination_matched:,}/{total:,}"
    )


# ============================================================
# 8. CHAY CHUONG TRINH
# ============================================================

def main():
    if not FLIGHT_DIR.exists():
        raise FileNotFoundError(
            f"Khong tim thay thu muc: {FLIGHT_DIR}"
        )

    flight_files = sorted(
        p for p in FLIGHT_DIR.glob("*.csv")
        if p.is_file()
        and not p.name.startswith("~$")
        and not p.stem.endswith("_weather_mapped")
    )

    if not flight_files:
        print("Khong tim thay CSV chuyen bay.")
        return

    weather = load_all_weather()
    airport_info = build_airport_info(weather)

    print(
        f"Chi ghep thoi tiet truoc thoi diem muc tieu "
        f"toi da {MAX_WEATHER_AGE_MINUTES} phut."
    )

    for flight_file in flight_files:
        process_flight_file(
            flight_file,
            weather,
            airport_info,
        )

    print("\nHoan tat mapping.")


if __name__ == "__main__":
    main()