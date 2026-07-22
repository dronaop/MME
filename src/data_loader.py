import csv
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_colleges.csv")

INT_FIELDS = {"annual_fees_inr", "last_year_cutoff_pct", "total_seats", "established_year"}
FLOAT_FIELDS = {"avg_placement_lpa"}
BOOL_FIELDS = {"hostel_available"}


def _coerce(field, value):
    value = (value or "").strip()
    if field in INT_FIELDS:
        return int(float(value)) if value else None
    if field in FLOAT_FIELDS:
        return float(value) if value else None
    if field in BOOL_FIELDS:
        return value.strip().lower() == "yes"
    if field == "courses_offered":
        return [c.strip() for c in value.split(";") if c.strip()]
    return value


def load_colleges(path: str = CSV_PATH):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = []
        for row in reader:
            rec = {field: _coerce(field, val) for field, val in row.items()}
            records.append(rec)
    return records


if __name__ == "__main__":
    recs = load_colleges()
    print(f"Loaded {len(recs)} colleges")
    print(recs[0])
