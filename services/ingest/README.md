# TreeMap Ingest Service

Python 3.12 data pipelines for municipal open tree registers and OpenStreetMap trees.

## Features

- Overpass API integration for `natural=tree`
- GeoJSON / WFS import with configurable YAML field mappings
- Spatial duplicate detection (< 3m) against register trees
- Strict provenance tracking (`source`, `source_id`, `licence`, `status`)

## Running Tests

```bash
uv sync
uv run pytest
```

## Importing Delhi's tree register

Configure `mappings/city_register_mapping.yaml` with the dataset's download URL
(or complete WFS `GetFeature` URL), actual source column names, source CRS,
public-land field/values, and the licence text before importing. The checked-in
mapping is intentionally unconfigured because no Delhi register URL, field
schema, or licence was supplied; the importer will refuse to run without a URL
and licence.

Supported downloads are GeoJSON, CSV, and zipped Shapefiles. The original
download is cached under `data/cache/` (ignored by Git). CSV coordinates and
vector geometries are transformed to EPSG:4326; rows without a valid point or
marked as non-public land are skipped. The importer keeps original source
properties in `raw_attributes` and upserts records using `(source, source_id)`.

Set `DATABASE_URL` to a Postgres connection using the Supabase service role,
then run from `services/ingest`:

```bash
uv run python -m ingest.city_register
```

The report is written to `out/report.md` (also ignored by Git). To use a WFS
endpoint or a dataset URL not stored in the mapping, pass `--url URL`.
The 50-row Delhi-shaped test sample is generated locally by pytest; it is
synthetic and is not source data.
