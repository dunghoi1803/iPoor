import csv
import json
from pathlib import Path
from typing import Any
from unicodedata import normalize


GEOJSON_FILES = {
    "old_63": "Việt Nam (tỉnh thành) - 63.geojson",
    "new_34": "Việt Nam (tỉnh thành) - 34.geojson",
}
GEO_NAME_FIELD = "ten_tinh"
GEO_CODE_FIELD = "ma_tinh"
PROCESSED_FILES = [
    "group1_values.csv",
    "group2_values.csv",
    "group3_values.csv",
    "group4_values.csv",
    "group5_values.csv",
    "group6_values.csv",
    "group7_values.csv",
    "group8_values.csv",
]
OUTPUT_FILE = "gis_indicator_values.csv"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = normalize("NFC", str(value))
    return " ".join(text.split()).strip().lower()


def load_geo_map(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    mapping: dict[str, dict[str, str]] = {}
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name = props.get(GEO_NAME_FIELD)
        code = props.get(GEO_CODE_FIELD)
        if not name or not code:
            continue
        mapping[normalize_text(name)] = {
            "geo_name": str(name),
            "geo_code": str(code),
        }
    return mapping


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data_dir = root.parent / "FE" / "data"
    processed_dir = data_dir / "processed"

    geo_maps = {
        key: load_geo_map(data_dir / filename)
        for key, filename in GEOJSON_FILES.items()
    }

    output_path = processed_dir / OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "indicator_code",
        "indicator_title",
        "metric",
        "year",
        "value",
        "geo_version",
        "geo_code",
        "geo_name",
    ]

    rows_out: list[dict[str, str]] = []

    for filename in PROCESSED_FILES:
        csv_path = processed_dir / filename
        if not csv_path.exists():
            continue
        with csv_path.open(encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                geo_version = row.get("geo_version", "old_63")
                geo_name = row.get("geo_name", "")
                geo_key = normalize_text(geo_name)
                geo_map = geo_maps.get(geo_version)
                if not geo_map:
                    continue
                geo_meta = geo_map.get(geo_key)
                if not geo_meta:
                    continue
                value = row.get("value")
                if value is None or value == "":
                    continue
                rows_out.append(
                    {
                        "indicator_code": row.get("indicator_code", ""),
                        "indicator_title": row.get("indicator_title", ""),
                        "metric": row.get("metric", ""),
                        "year": row.get("year", ""),
                        "value": value,
                        "geo_version": geo_version,
                        "geo_code": geo_meta["geo_code"],
                        "geo_name": geo_meta["geo_name"],
                    }
                )

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {output_path}")


if __name__ == "__main__":
    main()
