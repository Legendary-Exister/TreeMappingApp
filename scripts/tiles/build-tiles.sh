#!/usr/bin/env bash
# =============================================================================
# build-tiles.sh  —  Option A PMTiles pipeline
#
# Steps
# -----
#  1. Export trees from Postgres to GeoJSON Feature Sequence (geojsonseq)
#  2. Run tippecanoe to produce a PMTiles archive
#  3. Check the file is ≤ 50 MB
#  4. Upload to object storage (S3-compatible) with public-read and CORS for
#     range requests
#
# Required env vars
# -----------------
#   DATABASE_URL         Postgres connection string (service role)
#   STORAGE_BUCKET       Bucket name (e.g. treemap-tiles)
#   STORAGE_ENDPOINT     S3 endpoint URL (e.g. https://s3.amazonaws.com or
#                        https://<project>.supabase.co/storage/v1/s3)
#   AWS_ACCESS_KEY_ID    S3 access key
#   AWS_SECRET_ACCESS_KEY  S3 secret key
#   AWS_REGION           Bucket region (default: us-east-1)
#
# Optional
#   TILES_OUT_DIR        Working directory (default: out/tiles)
#   MAX_SIZE_MB          Fail if PMTiles exceeds this (default: 50)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TILES_OUT_DIR="${TILES_OUT_DIR:-$REPO_ROOT/out/tiles}"
GEOJSONSEQ="$TILES_OUT_DIR/trees.geojsonseq"
PMTILES="$TILES_OUT_DIR/trees.pmtiles"
MAX_SIZE_MB="${MAX_SIZE_MB:-50}"

# ---------------------------------------------------------------------------
# 0. Validate required tools
# ---------------------------------------------------------------------------
for cmd in node tippecanoe aws; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is not installed or not on PATH." >&2
    exit 1
  fi
done

mkdir -p "$TILES_OUT_DIR"

# ---------------------------------------------------------------------------
# 1. Export trees to GeoJSON-seq
# ---------------------------------------------------------------------------
echo "==> Exporting trees from Postgres…"
node "$SCRIPT_DIR/export-trees.mjs" "$GEOJSONSEQ"

# ---------------------------------------------------------------------------
# 2. Build PMTiles with tippecanoe
#
# Flags explained:
#   --output-to-directory / -o  — write a single PMTiles file
#   --minimum-zoom 10           — no tiles above zoom 10 (city-level)
#   --maximum-zoom 18           — street-level detail
#   --cluster-distance 10       — cluster points with neighbours within 10 px
#                                 below zoom 14; above 14 show individual trees
#   --cluster-maxzoom 13        — stop clustering at zoom ≥14
#   --include genus,...         — keep only these properties
#   --drop-densest-as-needed    — auto-thin to honour tile-size limits
#   --force                     — overwrite existing output
#   --read-parallel             — faster on multi-core machines
# ---------------------------------------------------------------------------
echo "==> Building PMTiles with tippecanoe…"
tippecanoe \
  --output="$PMTILES" \
  --minimum-zoom=10 \
  --maximum-zoom=18 \
  --cluster-distance=10 \
  --cluster-maxzoom=13 \
  --include=genus \
  --include=species \
  --include=status \
  --include=height_m \
  --include=circumference_m \
  --include=crown_diameter_m \
  --include=source \
  --include=leaf_cycle \
  --drop-densest-as-needed \
  --force \
  --read-parallel \
  --layer=trees \
  --name="TreeMap — city trees" \
  --description="Public trees exported from the TreeMap database. ODbL / OGDL." \
  "$GEOJSONSEQ"

# ---------------------------------------------------------------------------
# 3. Report tile count and file size; enforce the 50 MB cap
# ---------------------------------------------------------------------------
SIZE_BYTES=$(stat -c%s "$PMTILES" 2>/dev/null || stat -f%z "$PMTILES")
SIZE_MB=$(( SIZE_BYTES / 1024 / 1024 ))
TILE_COUNT=$(node - "$PMTILES" <<'EOF'
// Quick tile-count check using pmtiles CLI if available, otherwise skip
import { execSync } from 'node:child_process';
const f = process.argv[1];
try {
  const out = execSync(`pmtiles show "${f}"`, { encoding: 'utf8' });
  const m = out.match(/tile_count:\s*(\d+)/i) || out.match(/(\d+)\s+tiles/i);
  console.log(m ? m[1] : 'n/a');
} catch {
  console.log('n/a');
}
EOF
)

echo ""
echo "==> PMTiles build complete"
echo "    File      : $PMTILES"
echo "    Size      : ${SIZE_MB} MB (${SIZE_BYTES} bytes)"
echo "    Tile count: ${TILE_COUNT}"

if (( SIZE_MB > MAX_SIZE_MB )); then
  echo "ERROR: PMTiles file exceeds ${MAX_SIZE_MB} MB limit (${SIZE_MB} MB). Aborting upload." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. Upload to S3-compatible object storage
#    --acl public-read   — world-readable
#    Content-Type        — required for browsers to honour range requests
#    CORS on the bucket  — must be configured separately (see docs/tiles.md)
# ---------------------------------------------------------------------------
echo "==> Uploading to s3://${STORAGE_BUCKET}/trees.pmtiles …"
aws s3 cp "$PMTILES" "s3://${STORAGE_BUCKET}/trees.pmtiles" \
  --endpoint-url "${STORAGE_ENDPOINT:-}" \
  --region "${AWS_REGION:-us-east-1}" \
  --acl public-read \
  --content-type "application/x-protobuf" \
  --cache-control "public, max-age=3600, stale-while-revalidate=86400" \
  --no-progress

echo "==> Upload complete."
echo "    Public URL: ${STORAGE_ENDPOINT:-https://s3.amazonaws.com}/${STORAGE_BUCKET}/trees.pmtiles"
