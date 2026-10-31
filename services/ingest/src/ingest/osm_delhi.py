"""Delhi OSM tree importer.

Pipeline
--------
1. Query the Overpass API for natural=tree nodes inside Delhi's bounding box,
   caching the JSON response so each run makes at most one HTTP request.
2. Map each node's tags to our TreeRecord schema; reject implausible values.
3. Merge step: if an OSM tree lies within 3 m of a city_register tree already
   in the database, record the link in tree_links and fill missing register
   fields — never overwriting register values.
4. Insert genuinely new trees with source=osm.
5. Print / return a report of inserted, linked and rejected counts.

Running the importer twice is fully idempotent: rows are upserted on
(source, source_id) and tree_links is upserted on (osm_source_id, register_id).
"""

from __future__ import annotations

import argparse
import logging
import os
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingest.models import TreeRecord
from ingest.osm import OsmTreeImporter
from ingest.overpass import DELHI_BBOX, build_delhi_query, fetch_overpass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------

@dataclass
class ImportReport:
    """Counts returned after a completed import run."""

    nodes_fetched: int = 0
    inserted: int = 0
    linked: int = 0
    rejected: int = 0
    reject_reasons: dict[str, int] = field(default_factory=dict)

    def _inc_reject(self, reason: str) -> None:
        self.rejected += 1
        self.reject_reasons[reason] = self.reject_reasons.get(reason, 0) + 1

    def __str__(self) -> str:
        lines = [
            "OSM Delhi import report",
            f"  Nodes fetched : {self.nodes_fetched}",
            f"  Inserted      : {self.inserted}",
            f"  Linked        : {self.linked}",
            f"  Rejected      : {self.rejected}",
        ]
        for reason, count in sorted(self.reject_reasons.items()):
            lines.append(f"    {reason}: {count}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _load_register_trees(database_url: str) -> list[TreeRecord]:
    """Load all city_register trees from the database.

    Returns a list of lightweight TreeRecord objects (only the fields needed
    for proximity matching and gap-fill).
    """
    from psycopg2 import connect

    sql = """
        SELECT
            source_id,
            licence,
            status,
            genus,
            species,
            leaf_cycle,
            circumference_m,
            height_m,
            crown_diameter_m,
            extensions.ST_Y(geom::extensions.geometry) AS latitude,
            extensions.ST_X(geom::extensions.geometry) AS longitude
        FROM public.trees
        WHERE source = 'city_register'
    """
    with closing(connect(database_url)) as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    trees: list[TreeRecord] = []
    for row in rows:
        (
            source_id, licence, status, genus, species, leaf_cycle,
            circumference_m, height_m, crown_diameter_m, latitude, longitude,
        ) = row
        try:
            trees.append(
                TreeRecord(
                    source="city_register",
                    source_id=source_id,
                    licence=licence or "",
                    status=status,
                    genus=genus,
                    species=species,
                    leaf_cycle=leaf_cycle,
                    circumference_m=float(circumference_m) if circumference_m is not None else None,
                    height_m=float(height_m) if height_m is not None else None,
                    crown_diameter_m=float(crown_diameter_m) if crown_diameter_m is not None else None,
                    latitude=float(latitude),
                    longitude=float(longitude),
                )
            )
        except Exception as exc:  # noqa: BLE001  # skip individual bad rows
            logger.warning("Skipping malformed register row %s: %s", source_id, exc)
    return trees


def _upsert_osm_trees(database_url: str, records: list[TreeRecord]) -> None:
    """Insert / upsert OSM trees into public.trees."""
    if not records:
        return

    from psycopg2 import connect
    from psycopg2.extras import Json, execute_batch

    sql = """
        INSERT INTO public.trees (
            geom, source, source_id, licence, status,
            genus, species, leaf_cycle,
            circumference_m, height_m, crown_diameter_m,
            raw_attributes
        ) VALUES (
            extensions.ST_SetSRID(extensions.ST_MakePoint(%s, %s), 4326)::extensions.geography,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s
        )
        ON CONFLICT (source, source_id) DO UPDATE SET
            geom             = EXCLUDED.geom,
            licence          = EXCLUDED.licence,
            genus            = COALESCE(public.trees.genus,            EXCLUDED.genus),
            species          = COALESCE(public.trees.species,          EXCLUDED.species),
            leaf_cycle       = COALESCE(public.trees.leaf_cycle,       EXCLUDED.leaf_cycle),
            circumference_m  = COALESCE(public.trees.circumference_m,  EXCLUDED.circumference_m),
            height_m         = COALESCE(public.trees.height_m,         EXCLUDED.height_m),
            crown_diameter_m = COALESCE(public.trees.crown_diameter_m, EXCLUDED.crown_diameter_m),
            raw_attributes   = EXCLUDED.raw_attributes,
            updated_at       = NOW()
    """
    values = [
        (
            r.longitude, r.latitude,
            r.source, r.source_id, r.licence, r.status,
            r.genus, r.species, r.leaf_cycle,
            r.circumference_m, r.height_m, r.crown_diameter_m,
            Json(r.raw_attributes or {}),
        )
        for r in records
    ]
    with (
        closing(connect(database_url)) as conn,
        conn,
        conn.cursor() as cur,
    ):
        execute_batch(cur, sql, values, page_size=500)


def _upsert_tree_links(
    database_url: str,
    links: list[tuple[str, str, float]],
) -> None:
    """Upsert rows into public.tree_links.

    Each link is (osm_source_id, register_source_id, distance_m).
    The table is keyed on (osm_source_id, register_source_id) so re-runs are
    idempotent.
    """
    if not links:
        return

    from psycopg2 import connect
    from psycopg2.extras import execute_batch

    sql = """
        INSERT INTO public.tree_links (osm_source_id, register_source_id, distance_m)
        VALUES (%s, %s, %s)
        ON CONFLICT (osm_source_id, register_source_id) DO UPDATE SET
            distance_m = EXCLUDED.distance_m,
            updated_at = NOW()
    """
    with (
        closing(connect(database_url)) as conn,
        conn,
        conn.cursor() as cur,
    ):
        execute_batch(cur, sql, links, page_size=500)


def _update_register_tree(database_url: str, filled: TreeRecord) -> None:
    """Write gap-filled fields back to the city_register tree row."""
    from psycopg2 import connect

    sql = """
        UPDATE public.trees SET
            genus            = COALESCE(genus,            %s),
            species          = COALESCE(species,          %s),
            leaf_cycle       = COALESCE(leaf_cycle,       %s::public.leaf_cycle),
            circumference_m  = COALESCE(circumference_m,  %s),
            height_m         = COALESCE(height_m,         %s),
            crown_diameter_m = COALESCE(crown_diameter_m, %s),
            updated_at       = NOW()
        WHERE source = 'city_register' AND source_id = %s
    """
    with (
        closing(connect(database_url)) as conn,
        conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            sql,
            (
                filled.genus,
                filled.species,
                filled.leaf_cycle,
                filled.circumference_m,
                filled.height_m,
                filled.crown_diameter_m,
                filled.source_id,
            ),
        )


# ---------------------------------------------------------------------------
# Core importer function
# ---------------------------------------------------------------------------

def run_delhi_osm_import(
    *,
    cache_path: Path,
    database_url: str | None = None,
    bbox: tuple[float, float, float, float] = DELHI_BBOX,
    merge_threshold_m: float = 3.0,
    overpass_data: dict[str, Any] | None = None,
    register_trees: list[TreeRecord] | None = None,
) -> ImportReport:
    """Execute the full Delhi OSM import pipeline.

    Parameters
    ----------
    cache_path:
        File path for the Overpass JSON cache.
    database_url:
        Postgres connection string.  If *None* the DB steps are skipped
        (useful for tests that only want the parse / merge logic).
    bbox:
        Overpass bounding box (south, west, north, east).
    merge_threshold_m:
        Maximum distance in metres to link an OSM tree to a register tree.
    overpass_data:
        Pre-loaded Overpass JSON dict (bypasses network fetch; used in tests).
    register_trees:
        Pre-loaded register tree list (bypasses DB fetch; used in tests).
    """
    report = ImportReport()
    importer = OsmTreeImporter()

    # --- Step 1: Fetch or reuse Overpass data ---
    if overpass_data is None:
        query = build_delhi_query(bbox)
        overpass_data = fetch_overpass(query, cache_path)

    elements: list[dict[str, Any]] = [
        el for el in overpass_data.get("elements", []) if el.get("type") == "node"
    ]
    report.nodes_fetched = len(elements)
    logger.info("Processing %d OSM nodes …", report.nodes_fetched)

    # --- Step 2: Load existing register trees ---
    if register_trees is None:
        if database_url:
            register_trees = _load_register_trees(database_url)
        else:
            register_trees = []

    # --- Step 3 & 4: Parse, validate, merge ---
    to_insert: list[TreeRecord] = []
    links: list[tuple[str, str, float]] = []           # (osm_id, reg_id, dist)
    filled_registers: list[TreeRecord] = []            # enriched register rows

    for element in elements:
        record = importer.parse_osm_node(element)
        if record is None:
            report._inc_reject("parse_error")
            continue

        is_dup, matched, dist = importer.check_duplicate(
            record, register_trees, threshold_m=merge_threshold_m
        )

        if is_dup and matched is not None and dist is not None:
            links.append((record.source_id, matched.source_id, round(dist, 3)))
            filled = importer.merge_fill(matched, record)
            if filled is not matched:
                filled_registers.append(filled)
            report.linked += 1
        else:
            to_insert.append(record)

    # --- Step 5: Persist to database ---
    if database_url:
        _upsert_osm_trees(database_url, to_insert)
        _upsert_tree_links(database_url, links)
        for filled in filled_registers:
            _update_register_tree(database_url, filled)

    report.inserted = len(to_insert)
    logger.info("%s", report)
    return report


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Import OSM natural=tree nodes for Delhi"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(__file__).parents[2] / "data" / "cache",
        help="Directory for the cached Overpass JSON response",
    )
    parser.add_argument(
        "--merge-threshold-m",
        type=float,
        default=3.0,
        help="Distance threshold in metres for linking to a register tree (default: 3)",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("Set DATABASE_URL to a Postgres connection using the service role")

    cache_path = args.cache_dir / "osm_delhi_trees.json"
    report = run_delhi_osm_import(
        cache_path=cache_path,
        database_url=database_url,
        merge_threshold_m=args.merge_threshold_m,
    )
    print(report)


if __name__ == "__main__":
    main()
