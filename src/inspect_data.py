
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "raw"

flights = pd.read_parquet(DATA / "flights.parquet")
airports = pd.read_parquet(DATA / "airports.parquet")
airlines = pd.read_parquet(DATA / "airlines.parquet")

print("Kich thuoc flights:", flights.shape)
print("Cac cot flights:")
print(flights.columns.tolist())

print("\n5 dong dau:")
print(flights.head())

print("\nThong ke gia tri thieu:")
print(
    flights.isna().sum()
    .sort_values(ascending=False)
    .head(20)
)

print("\nAirports:", airports.shape)
print(airports.head())

print("\nAirlines:", airlines.shape)
print(airlines.head())
