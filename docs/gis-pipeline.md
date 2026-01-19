# GIS Pipeline

This project builds GIS indicators from the Excel source into a CSV used by the API.
The pipeline runs locally and writes to `FE/data/processed`.

## Inputs

- Excel source (group 1):
  - `FE/data/So lieu ve ban do 27 Nov 2025_2.xlsx`
- Province label maps (canonical names):
  - `FE/data/processed/geo_labels_63.json`
  - `FE/data/processed/geo_labels_34.json`
- Province GeoJSON (name -> code):
  - `FE/data/Việt Nam (tỉnh thành) - 63.geojson`
  - `FE/data/Việt Nam (tỉnh thành) - 34.geojson`

## Output files

- Intermediate (group 1):
  - `FE/data/processed/group1_values.csv`
  - Includes `geo_name` and `geo_code`
- Final dataset used by API:
  - `FE/data/processed/gis_indicator_values.csv`

## Pipeline steps

1) Parse Excel and normalize names, attach geo codes:
```
python3 backend/scripts/data_pipeline/parse_group1.py
```

2) Build the final GIS dataset:
```
python3 backend/scripts/data_pipeline/build_gis_dataset.py
```

## How name resolution works

Name resolution happens in:
- `backend/scripts/data_pipeline/geo_name_matcher.py`

It normalizes labels by:
- stripping diacritics
- removing stopwords (tinh, thanh, pho)
- expanding abbreviations (tp -> thanh pho)
- applying aliases (e.g., dac lak -> dak lak)
- fuzzy matching if needed

The result is a canonical `geo_name` and a `geo_code` derived from GeoJSON.

## API data source

The API reads:
- `FE/data/processed/gis_indicator_values.csv`

If the API container was built before the CSV update, it will still serve the old file.

To avoid rebuilds, mount the data directory:
```
api:
  volumes:
    - ./FE/data:/app/FE/data
```

## Troubleshooting

- Missing province in GIS:
  - Check `group1_values.csv` for the label and `geo_code`.
  - If `geo_code` is empty, add an alias in `geo_name_matcher.py`.
- Indicator still shows after deleting rows:
  - Ensure the API container sees the updated CSV (rebuild or mount).
