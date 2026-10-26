
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
df = pd.read_parquet(BASE / "data" / "raw" / "flights.parquet")

print("1. KICH THUOC")
print(f"So dong: {len(df):,}")
print(f"So cot: {len(df.columns)}")

print("\n2. SO GIA TRI THIEU")
missing = df.isna().sum()
missing_pct = (missing / len(df) * 100).round(2)

report = pd.DataFrame({
    "missing_count": missing,
    "missing_percent": missing_pct,
})

print(report.sort_values("missing_percent", ascending=False).head(20))

print("\n3. SO BAN GHI TRUNG HOAN TOAN")
print(df.duplicated().sum())

print("\n4. TINH TRANG CHUYEN BAY")
print("So chuyen huy:", df["CANCELLED"].sum())
print("So chuyen chuyen huong:", df["DIVERTED"].sum())

print("\n5. THONG KE DO TRE DEN NOI")
print(df["ARRIVAL_DELAY"].describe())

print("\n6. TY LE CHUYEN DEN TRE TU 15 PHUT")
valid = df["ARRIVAL_DELAY"].dropna()
print((valid >= 15).mean() * 100, "%")
