
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"

# Chuyển dữ liệu chuyến bay
flights = pd.read_parquet(RAW / "flights.parquet")
flights.to_csv(
    RAW / "flights_2015.csv",
    index=False,
    encoding="utf-8-sig",
)
print("Da xuat flights_2015.csv", flights.shape)
del flights

# Chuyển bảng sân bay
airports = pd.read_parquet(RAW / "airports.parquet")
airports.to_csv(
    RAW / "airports.csv",
    index=False,
    encoding="utf-8-sig",
)
print("Da xuat airports.csv", airports.shape)
del airports

# Chuyển bảng hãng hàng không
airlines = pd.read_parquet(RAW / "airlines.parquet")
airlines.to_csv(
    RAW / "airlines.csv",
    index=False,
    encoding="utf-8-sig",
)
print("Da xuat airlines.csv", airlines.shape)

print("HOAN TAT")
