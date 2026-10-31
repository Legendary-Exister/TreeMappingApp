# Vector Tiles for the Tree Layer

TreeMap serves the tree layer as [PMTiles](https://github.com/protomaps/PMTiles) —
a single-file, cloud-optimised archive that the browser streams with HTTP range
requests. No tile server is required.

---

## Option A — PMTiles (implemented, default)

```
Postgres → GeoJSON Feature Sequence → tippecanoe → trees.pmtiles → S3 / object storage
                                                                         ↓
                                                                   MapLibre GL (pmtiles://)
```

### How it works

1. **Export** (`scripts/tiles/export-trees.mjs`)  
   Streams every row from `public.trees` as a [GeoJSON Feature Sequence](https://www.rfc-editor.org/rfc/rfc8142)
   (newline-delimited GeoJSON, one feature per line) into `out/tiles/trees.geojsonseq`.
   Only the attributes kept in tiles are projected: `genus`, `species`, `status`,
   `height_m`, `circumference_m`, `crown_diameter_m`, `source`, `leaf_cycle`.

2. **Build** (`scripts/tiles/build-tiles.sh` via tippecanoe)
   | Parameter | Value |
   |-----------|-------|
   | Min zoom  | 10 (city overview) |
   | Max zoom  | 18 (street level) |
   | Clustering| Points within 10 px are clustered at zoom ≤ 13 |
   | Properties | genus, species, status, height_m, circumference_m, crown_diameter_m, source, leaf_cycle |
   | Thinning  | `--drop-densest-as-needed` auto-reduces at low zoom |
   | Size cap  | Build fails if the file exceeds **50 MB** |

3. **Upload** — AWS CLI copies the file to the configured S3-compatible bucket
   with `--acl public-read` and `Cache-Control: public, max-age=3600`.

4. **Web map** (`apps/web/components/Map.tsx`)  
   On load, the `pmtiles` JS library registers a `pmtiles://` protocol handler
   with MapLibre GL so the browser fetches tile slices directly from the PMTiles
   archive using HTTP range requests. No tile-server proxy is involved.
   - Zoom < 14: clustered circles coloured by cluster size.
   - Zoom ≥ 14: individual circles coloured by `status`
     (green = verified, yellow = unverified, red = disputed, grey = removed).
   - Click a tree to see species and height.

### Build the tiles locally

```bash
# 1. Install tippecanoe (macOS)
brew install tippecanoe
# or Ubuntu: build from source (see the nightly CI workflow for steps)

# 2. Set required environment variables
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
export STORAGE_BUCKET="treemap-tiles"
export STORAGE_ENDPOINT="https://s3.amazonaws.com"     # or your custom endpoint
export AWS_ACCESS_KEY_ID="…"
export AWS_SECRET_ACCESS_KEY="…"
export AWS_REGION="us-east-1"

# 3. Run
pnpm tiles:build
```

The script prints the tile count and file size before uploading:

```
==> PMTiles build complete
    File      : out/tiles/trees.pmtiles
    Size      : 18 MB (18874368 bytes)
    Tile count: 284721
```

### Object storage CORS configuration

The browser fetches tile chunks with `Range` headers. The bucket **must** have a CORS rule:

```json
[
  {
    "AllowedHeaders": ["Range"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": ["Accept-Ranges", "Content-Range", "Content-Length", "ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

For **Supabase Storage** (S3-compatible), configure CORS in the Supabase dashboard
under Storage → Buckets → CORS settings, or via the Supabase CLI.

### Nightly CI

`.github/workflows/tiles-nightly.yml` rebuilds `trees.pmtiles` every night at 02:00 UTC
and uploads it. Required GitHub Actions secrets:

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | Postgres connection string (service role) |
| `STORAGE_BUCKET` | Bucket name |
| `STORAGE_ENDPOINT` | S3 endpoint URL (blank for AWS) |
| `AWS_ACCESS_KEY_ID` | Access key |
| `AWS_SECRET_ACCESS_KEY` | Secret key |
| `AWS_REGION` | Bucket region |

The PMTiles file is also saved as a workflow artifact for 7 days.

To trigger manually: **Actions → Nightly Tiles Build → Run workflow**.

### City scale

For a city of 100 000 trees:

| Layer | Compressed size estimate |
|-------|--------------------------|
| 100 k trees, zoom 10–18 | ≈ 12–25 MB |
| 500 k trees, zoom 10–18 | ≈ 40–70 MB (may need zoom cap at 16) |

If the 50 MB cap is hit, either reduce `--maximum-zoom` to 16 or enable
`--drop-fraction-as-needed` in `build-tiles.sh`. Both are one-line changes.

---

## Option B — Live tiles from PostGIS with Martin

[Martin](https://martin.maplibre.org/) serves vector tiles directly from Postgres
using a SQL function source. There is **no build step** — edits appear in the map
immediately after the database row is committed.

### When to switch to Option B

| Condition | Recommendation |
|-----------|----------------|
| Edits (citizen/reviewer updates) must be visible **within seconds** | Switch to Martin |
| Dataset > 500 k trees and PMTiles file exceeds 50 MB | Switch to Martin |
| You need attribute filtering in the tile URL (e.g. `?status=verified`) | Switch to Martin |
| Nightly latency (< 24 h stale) is acceptable and cost matters | Stay on Option A |

### How to add Martin

1. **Run Martin** alongside Supabase:
   ```yaml
   # docker-compose.yml (snippet)
   martin:
     image: ghcr.io/maplibre/martin:latest
     environment:
       DATABASE_URL: postgresql://postgres:postgres@db:5432/postgres
     ports:
       - "3001:3000"
   ```

2. **Create a function source** in Supabase:
   ```sql
   -- supabase/migrations/YYYYMMDD_martin_trees_fn.sql
   CREATE OR REPLACE FUNCTION public.trees_tile(z int, x int, y int)
   RETURNS bytea
   LANGUAGE sql STABLE PARALLEL SAFE
   AS $$
     SELECT extensions.ST_AsMVT(tile, 'trees', 4096, 'geom')
     FROM (
       SELECT
         extensions.ST_AsMVTGeom(
           geom::extensions.geometry,
           extensions.ST_TileEnvelope(z, x, y),
           4096, 64, true
         ) AS geom,
         genus, species, status, height_m,
         circumference_m, crown_diameter_m, leaf_cycle
       FROM public.trees
       WHERE geom && extensions.ST_TileEnvelope(z, x, y, margin => 64.0/4096)
     ) tile
     WHERE geom IS NOT NULL
   $$;
   ```

3. **Update the web map** — replace `pmtiles://` source with a TileJSON source:
   ```ts
   map.addSource('trees', {
     type: 'vector',
     tiles: ['http://martin-host:3001/trees_tile/{z}/{x}/{y}'],
     minzoom: 10,
     maxzoom: 18,
   });
   ```
   The layer definitions in `Map.tsx` remain identical.

4. **Remove** the nightly workflow and `pnpm tiles:build` script (or keep them
   as a static backup / CDN fallback).

---

## Architecture decision

See **ADR-009** in [`docs/decisions.md`](decisions.md).
