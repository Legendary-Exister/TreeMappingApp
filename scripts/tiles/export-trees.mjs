#!/usr/bin/env node
/**
 * export-trees.mjs
 *
 * Streams every tree from the public.trees table as a GeoJSON Feature Sequence
 * (newline-delimited GeoJSON, RFC 8142) to a file that tippecanoe can read
 * directly with --read-parallel.
 *
 * Only the fields kept in vector tiles are projected:
 *   id, genus, species, status, height_m, circumference_m, crown_diameter_m,
 *   source, leaf_cycle
 *
 * Usage:
 *   DATABASE_URL=postgres://... node scripts/tiles/export-trees.mjs [outFile]
 *   (defaults to out/trees.geojsonseq)
 *
 * The script exits with code 1 on error so the wrapper can abort the pipeline.
 */

import { createWriteStream } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import pg from 'pg';

const { Client } = pg;

const OUT_FILE = resolve(process.argv[2] ?? 'out/trees.geojsonseq');
const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  console.error('ERROR: DATABASE_URL environment variable is not set.');
  process.exit(1);
}

// ------------------------------------------------------------------
// Query — project only the columns kept in the tile attributes.
// Use ST_AsGeoJSON for correct WGS-84 GeoJSON point output.
// ------------------------------------------------------------------
const SQL = `
SELECT
  jsonb_build_object(
    'type',       'Feature',
    'geometry',   extensions.ST_AsGeoJSON(geom)::jsonb,
    'properties', jsonb_build_object(
      'id',              id,
      'genus',           genus,
      'species',         species,
      'status',          status,
      'height_m',        height_m,
      'circumference_m', circumference_m,
      'crown_diameter_m',crown_diameter_m,
      'source',          source,
      'leaf_cycle',      leaf_cycle
    )
  ) AS feature
FROM public.trees
ORDER BY id
`;

async function main() {
  await mkdir(dirname(OUT_FILE), { recursive: true });

  const client = new Client({ connectionString: DATABASE_URL });
  await client.connect();

  const out = createWriteStream(OUT_FILE, { encoding: 'utf8' });

  let count = 0;
  const startMs = Date.now();

  // Use a cursor via pg's query-streaming interface
  const query = new pg.Query(SQL);

  await new Promise((resolve, reject) => {
    out.on('error', reject);

    client.query(query);

    query.on('row', (row) => {
      out.write(JSON.stringify(row.feature) + '\n');
      count += 1;
      if (count % 10_000 === 0) {
        process.stdout.write(`  exported ${count.toLocaleString()} trees…\r`);
      }
    });

    query.on('end', resolve);
    query.on('error', reject);
  });

  out.end();
  await new Promise((res, rej) => {
    out.on('finish', res);
    out.on('error', rej);
  });

  await client.end();

  const elapsed = ((Date.now() - startMs) / 1000).toFixed(1);
  console.log(`\nExported ${count.toLocaleString()} trees → ${OUT_FILE} (${elapsed}s)`);
  return count;
}

main().catch((err) => {
  console.error('Export failed:', err.message);
  process.exit(1);
});
