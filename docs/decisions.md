# Architecture Decisions (ADR)

## ADR-001: Monorepo Architecture with pnpm & Turborepo

- **Status:** Accepted
- **Context:** We need a unified repository sharing code between Next.js web app, Expo mobile app, shared types, and API client, alongside Python ingest pipelines.
- **Decision:** Use pnpm workspaces with Turborepo for fast builds, task pipelining, and caching.

## ADR-002: Map Rendering with MapLibre GL

- **Status:** Accepted
- **Context:** The application maps city trees without proprietary map vendors (no Google Maps API fees, no Mapbox token lock-in).
- **Decision:** Use MapLibre GL (`maplibre-gl` on Web, `@maplibre/maplibre-react-native` on Mobile) with OpenFreeMap / PMTiles vector tiles.

## ADR-003: Postgres + PostGIS with Supabase

- **Status:** Accepted
- **Context:** High-performance spatial indexing, authentication, row-level security, and edge functions.
- **Decision:** Use Supabase with Postgres and PostGIS extension. Trees store `geography(Point, 4326)` with GIST indexing for spatial radius queries (`trees_near`).

## ADR-004: Python 3.12 for Data Ingest Services

- **Status:** Accepted
- **Context:** City tree registers and OpenStreetMap trees require geo-spatial data manipulation (GeoPandas, Shapely, PyPGL, Overpass).
- **Decision:** Use Python 3.12 managed with Astral `uv` for isolated, fast, and reproducible virtual environment workflows.

## ADR-005: Strict Schema & Provenance

- **Status:** Accepted
- **Context:** Data originates from city registers, OpenStreetMap, and citizen science. Attribution and provenance must be strictly preserved.
- **Decision:** Every tree record retains `source`, `source_id`, `licence`, and `status`. Field names map to OSM tree tags (`genus`, `species`, `circumference_m`, `height_m`, `crown_diameter_m`, `leaf_cycle`). Zod schemas in `@treemap/types` validate inputs.

## ADR-006: Row Level Security & Repeatable Ingestion

- **Status:** Accepted
- **Context:** Tree data is public for viewing, but ingestion from municipal data and OSM must be restricted to authenticated automated pipelines (`service_role`), while citizen contributions must be signed and attributed.
- **Decision:**
  - `trees` and verified `photos` are world-readable (`anon` and `authenticated`).
  - Unique composite index on `(source, source_id)` ensures idempotent, repeatable pipeline runs.
  - Only `service_role` can insert or modify imported trees (`city_register`, `osm`).
  - Signed-in users can submit observations and photos; only authors can edit or delete their own submissions.
  - Citizen-submitted trees must start as `unverified`; clients cannot mark photos verified or create reviewer profiles.
  - The security-definer tree submission RPC is restricted to authenticated callers.
  - Verifications can only be written by authenticated users with the `reviewer` or `admin` role in `public.profiles`.

## ADR-007: Configurable Delhi Register Import

- **Status:** Accepted
- **Context:** Delhi register downloads and field schemas must remain separate from importer code, and only public-land trees may be seeded.
- **Decision:** Configure source URL, format, CRS, licence, field mappings, and public-land values in YAML. Cache downloaded source data outside version control, reproject to EPSG:4326, retain original attributes, and upsert on `(source, source_id)`. Require the dataset URL and licence before running because neither was provided with the initial Delhi request.

## ADR-008: OSM Delhi Importer with Overpass API and 3 m Merge

- **Status:** Accepted
- **Context:** OpenStreetMap holds thousands of `natural=tree` nodes for Delhi, but importing them blindly would create duplicates of city-register rows already in the database.
- **Decision:**
  - **Fetch:** Query the Overpass API once per run (`overpass.py`) for `natural=tree` nodes inside Delhi's bounding box (28.404 N–28.883 N, 76.838 E–77.347 E). The response is cached as `data/cache/osm_delhi_trees.json` so subsequent runs read from disk.  A descriptive `User-Agent` header identifies the project.  Transient failures retry with exponential back-off (max 5 attempts, starting at 5 s, capped at 120 s).
  - **Tag mapping:** `genus`, `species`, `taxon` → `genus`/`species`; `circumference` → `circumference_m` (metres); `height` → `height_m`; `diameter_crown` / `crown_diameter` → `crown_diameter_m`; `leaf_cycle` (normalising `semi-evergreen` → `semi_evergreen`). Impossible values are silently set to `None`: circumference > 43 m, height > 116 m, crown diameter > 60 m.
  - **Provenance:** `source = 'osm'`, `source_id = 'node/<osm_id>'`, `licence = 'ODbL (© OpenStreetMap contributors)'`.
  - **Merge (3 m rule):** For each OSM node, the Haversine distance to every city-register tree is computed.  If the nearest is ≤ 3 m, the pair is recorded in `public.tree_links` (upserted on `(osm_source_id, register_source_id)`) and empty fields on the register row are filled from OSM — register values are never overwritten.  Only trees with no register match within 3 m are inserted into `public.trees`.
  - **Idempotency:** `public.trees` is upserted on `(source, source_id)`; `public.tree_links` is upserted on `(osm_source_id, register_source_id)`. Re-running produces identical state.
  - **Reporting:** The importer prints counts of inserted, linked, and rejected nodes plus per-reason reject breakdowns.
  - **`tree_links` table:** Added in migration `20261031000000_create_tree_links.sql` with RLS (world-readable, service-role write).

## ADR-009: Vector Tiles — PMTiles (Option A) with Martin fallback (Option B)

- **Status:** Accepted
- **Context:** The tree layer must be visible in MapLibre GL on web and mobile without a proprietary tile service. Two approaches were considered: a nightly-built static PMTiles file (Option A) and a live PostGIS function source served by Martin (Option B).
- **Decision:** Implement Option A by default.
  - `scripts/tiles/export-trees.mjs` exports `public.trees` as GeoJSON Feature Sequence.
  - `scripts/tiles/build-tiles.sh` runs tippecanoe (zoom 10–18, cluster points below zoom 14, keep genus / species / status / height_m) and uploads the resulting `trees.pmtiles` to S3-compatible object storage.
  - `pnpm tiles:build` is the single entry point; `.github/workflows/tiles-nightly.yml` rebuilds nightly at 02:00 UTC.
  - The web map registers the `pmtiles://` protocol via the `pmtiles` JS library and streams tile chunks with HTTP range requests — no tile-server proxy.
  - The build fails if the file exceeds 50 MB, catching runaway datasets early.
  - Option B (Martin) is documented in `docs/tiles.md` and should be adopted when citizen/reviewer edits must appear within seconds or the dataset exceeds 500 k trees.
