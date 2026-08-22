"""
Download and cache daily Fama-French 3 factors (Mkt-RF, SMB, HML, RF) plus
the momentum factor (Mom) from Ken French's data library, for the factor
regression in analyze.py. Used to test whether the overnight/intraday
return split is a distinct effect or repackaged exposure to known risk
factors (market, size, value, momentum).
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import urllib.request

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FACTORS_DIR = DATA_DIR / "factors"
FACTORS_DIR.mkdir(parents=True, exist_ok=True)

FF3_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip"
MOM_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_zip_csv(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    name = zf.namelist()[0]
    return zf.read(name).decode("utf-8", errors="ignore")


def parse_ff_csv(text: str) -> dict:
    """Parse a Ken French daily CSV (header rows + footer copyright text)
    into {date_str: {col: float_value_as_decimal}}."""
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        parts = line.split(",")
        if len(parts) >= 2 and parts[0].strip() == "" and all(p.strip() for p in parts[1:]):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("could not find header row")

    cols = [c.strip() for c in lines[header_idx].split(",")[1:]]
    out = {}
    for line in lines[header_idx + 1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(cols) + 1:
            continue
        date_str = parts[0]
        if not (date_str.isdigit() and len(date_str) == 8):
            continue
        date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        try:
            values = {cols[i]: float(parts[i + 1]) / 100.0 for i in range(len(cols))}
        except ValueError:
            continue
        out[date] = values
    return out


def main():
    print("Fetching Fama-French 3 daily factors...")
    ff3 = parse_ff_csv(download_zip_csv(FF3_URL))
    print(f"  {len(ff3)} dates, {min(ff3)} to {max(ff3)}")

    print("Fetching momentum daily factor...")
    mom = parse_ff_csv(download_zip_csv(MOM_URL))
    print(f"  {len(mom)} dates, {min(mom)} to {max(mom)}")

    all_dates = sorted(set(ff3) & set(mom))
    out_path = FACTORS_DIR / "ff_factors_daily.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "mkt_rf", "smb", "hml", "mom", "rf"])
        for d in all_dates:
            row = ff3[d]
            writer.writerow([d, row["Mkt-RF"], row["SMB"], row["HML"], mom[d]["Mom"], row["RF"]])
    print(f"Saved {len(all_dates)} rows -> {out_path}")


if __name__ == "__main__":
    main()
