import csv
import json
from pathlib import Path

from geo_name_matcher import (
    build_label_lookup,
    normalize_geo_code,
    normalize_name_key,
    resolve_geo_name,
)


GEOJSON_FILES = {
    "old_63": "Việt Nam (tỉnh thành) - 63.geojson",
    "new_34": "Việt Nam (tỉnh thành) - 34.geojson",
}
GEO_NAME_FIELD = "ten_tinh"
GEO_CODE_FIELD = "ma_tinh"
FIELD_GEO_CODE = "geo_code"
FIELD_GEO_NAME = "geo_name"
FIELD_GEO_VERSION = "geo_version"
FIELD_VALUE = "value"
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


def normalize_geo_key(value: str) -> str:
    return normalize_name_key(value)


def load_geo_map(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    mapping: dict[str, dict[str, str]] = {}
    code_map: dict[str, str] = {}
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name = props.get(GEO_NAME_FIELD)
        code = props.get(GEO_CODE_FIELD)
        if not name or not code:
            continue
        normalized_name = normalize_geo_key(name)
        geo_name = str(name)
        geo_code = str(code)
        mapping[normalized_name] = {
            FIELD_GEO_NAME: geo_name,
            FIELD_GEO_CODE: geo_code,
        }
        code_map[geo_code] = geo_name
    return mapping, code_map


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    data_dir = root.parent / "FE" / "data"
    processed_dir = data_dir / "processed"

    geo_maps = {}
    geo_code_maps = {}
    for version, filename in GEOJSON_FILES.items():
        name_map, code_map = load_geo_map(data_dir / filename)
        geo_maps[version] = name_map
        geo_code_maps[version] = code_map
    geo_name_lookup = {
        version: build_label_lookup(
            {meta[FIELD_GEO_CODE]: meta[FIELD_GEO_NAME] for meta in geo_map.values()}
        )
        for version, geo_map in geo_maps.items()
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
                geo_version = row.get(FIELD_GEO_VERSION, "old_63")
                geo_name = row.get(FIELD_GEO_NAME, "")
                geo_key = normalize_geo_key(geo_name)
                geo_map = geo_maps.get(geo_version)
                if not geo_map:
                    continue
                raw_geo_code = row.get(FIELD_GEO_CODE, "")
                normalized_code = normalize_geo_code(raw_geo_code)
                geo_meta = None
                if normalized_code:
                    geo_name_from_code = geo_code_maps.get(geo_version, {}).get(normalized_code)
                    if geo_name_from_code:
                        geo_meta = {
                            FIELD_GEO_NAME: geo_name_from_code,
                            FIELD_GEO_CODE: normalized_code,
                        }
                if not geo_meta:
                    geo_meta = geo_map.get(geo_key)
                if not geo_meta:
                    lookup = geo_name_lookup.get(geo_version, {})
                    resolved_name = resolve_geo_name(geo_name, lookup)
                    if resolved_name != geo_name:
                        geo_key = normalize_geo_key(resolved_name)
                        geo_meta = geo_map.get(geo_key)
                if not geo_meta:
                    continue
                value = row.get(FIELD_VALUE)
                if value is None or value == "":
                    continue
                rows_out.append(
                    {
                        "indicator_code": row.get("indicator_code", ""),
                        "indicator_title": row.get("indicator_title", ""),
                        "metric": row.get("metric", ""),
                        "year": row.get("year", ""),
                        "value": value,
                        FIELD_GEO_VERSION: geo_version,
                        FIELD_GEO_CODE: geo_meta[FIELD_GEO_CODE],
                        FIELD_GEO_NAME: geo_meta[FIELD_GEO_NAME],
                    }
                )

    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {output_path}")


if __name__ == "__main__":
    main()
