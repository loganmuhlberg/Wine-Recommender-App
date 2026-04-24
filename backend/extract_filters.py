"""
extract_filters.py

Runs a short script to get all unique countries, varietals, and regions from the csv dataset
For autofill in the taste profile and recommendation sidebar filters in the frontend.
"""

import json
import pandas as pd
from pathlib import Path

CSV_PATH    = Path(__file__).parent.parent / "data" / "wines_db.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "frontend" / "filter_options.json"

df = pd.read_csv(CSV_PATH)

def clean_list(series) -> list[str]:
    """Drop nulls, strip whitespace, sort, deduplicate."""
    return sorted(set(
        v.strip() for v in series.dropna().unique()
        if isinstance(v, str) and v.strip()
    ))

options = {
    "countries": clean_list(df["country"]),
    "regions":   clean_list(df["region_1"]),
    "varietals": clean_list(df["variety"])
}

print(f"Countries: {len(options['countries'])}")
print(f"Regions:   {len(options['regions'])}")
print(f"Varietals: {len(options['varietals'])}")

with open(OUTPUT_PATH, "w") as f:
    json.dump(options, f, indent=2)

print(f"\nWritten to {OUTPUT_PATH}")