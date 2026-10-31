"""Tests for the Delhi OSM import pipeline (osm_delhi.py).

All tests are unit-level — no network, no database.  Fixture data is
constructed inline so the suite runs offline and stays fast.
"""
from __future__ import annotations

from pathlib import Path

from ingest.models import TreeRecord
from ingest.osm import haversine_distance_m
from ingest.osm_delhi import ImportReport, run_delhi_osm_import

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(
    node_id: int,
    lat: float,
    lon: float,
    **tags: str,
) -> dict:
    """Build a minimal Overpass element dict."""
    return {"type": "node", "id": node_id, "lat": lat, "lon": lon, "tags": tags}


def _overpass(elements: list[dict]) -> dict:
    return {"version": 0.6, "elements": elements}


def _register_tree(source_id: str, lat: float, lon: float, **kwargs) -> TreeRecord:
    defaults: dict = {
        "source": "city_register",
        "licence": "OGDL-India",
        "status": "unverified",
        "latitude": lat,
        "longitude": lon,
    }
    defaults.update(kwargs)
    return TreeRecord(source_id=source_id, **defaults)


# ---------------------------------------------------------------------------
# Fixture: Delhi bounding box OSM data
# ---------------------------------------------------------------------------

# Approximate Delhi centre
_DELHI_LAT = 28.6500
_DELHI_LON = 77.2000

FIXTURE_ELEMENTS = [
    # 0: Valid tree, no near register tree → should be inserted
    # Node 1001 is ~50 m south of _DELHI_LAT — clearly > 3 m from REG-001.
    _node(1001, _DELHI_LAT - 0.00045, _DELHI_LON,
          natural="tree", genus="Ficus", species="religiosa",
          circumference="2.5", height="15", diameter_crown="9",
          leaf_cycle="evergreen"),

    # 1: Valid tree within 2 m of a register tree → should be linked
    _node(1002, _DELHI_LAT + 0.000015, _DELHI_LON,   # ~1.7 m north
          natural="tree", genus="Azadirachta", species="indica",
          circumference="1.8"),

    # 2: Valid tree — implausible circumference (> 43 m) → inserted but
    #    circumference_m must be None
    _node(1003, _DELHI_LAT + 0.01, _DELHI_LON,
          natural="tree", circumference="50"),

    # 3: Valid tree — implausible height (> 116 m) → inserted but height_m None
    _node(1004, _DELHI_LAT + 0.02, _DELHI_LON,
          natural="tree", height="120"),

    # 4: Non-node element (way) — must be silently skipped
    {"type": "way", "id": 9999, "nodes": [1, 2, 3]},

    # 5: Node without coordinates → parse_osm_node returns None → rejected
    {"type": "node", "id": 5000, "tags": {"natural": "tree"}},
]

# The register tree that node 1002 should be linked to (within 2 m)
REGISTER_TREES = [
    _register_tree("REG-001", _DELHI_LAT + 0.000015, _DELHI_LON,
                   genus="Azadirachta", species="indica"),
]


# ---------------------------------------------------------------------------
# Pipeline integration tests (no DB)
# ---------------------------------------------------------------------------

def test_basic_pipeline_counts(tmp_path: Path):
    """Inserted + linked + rejected must account for all valid nodes."""
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(FIXTURE_ELEMENTS),
        register_trees=REGISTER_TREES,
    )
    # Node 1002 is within 2 m of REG-001 → linked
    assert report.linked == 1
    # Nodes 1001, 1003, 1004 are new → inserted
    assert report.inserted == 3
    # Node 5000 has no coordinates → rejected
    assert report.rejected == 1


def test_nodes_fetched_counts_only_node_elements(tmp_path: Path):
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(FIXTURE_ELEMENTS),
        register_trees=[],
    )
    # 5 node-type elements (the way is excluded)
    assert report.nodes_fetched == 5


def test_idempotency_second_run_same_counts(tmp_path: Path):
    """Running the pipeline twice with identical data produces the same counts."""
    kwargs = {
        "cache_path": tmp_path / "cache.json",
        "database_url": None,
        "overpass_data": _overpass(FIXTURE_ELEMENTS),
        "register_trees": REGISTER_TREES,
    }
    r1 = run_delhi_osm_import(**kwargs)
    r2 = run_delhi_osm_import(**kwargs)
    assert r1.inserted == r2.inserted
    assert r1.linked == r2.linked
    assert r1.rejected == r2.rejected


# ---------------------------------------------------------------------------
# Plausibility rules
# ---------------------------------------------------------------------------

def test_implausible_circumference_field_is_none_not_rejected(tmp_path: Path):
    """A tree with circumference > 43 m is INSERTED with circumference_m=None,
    not counted as rejected (the tree itself is valid)."""
    elements = [_node(3001, _DELHI_LAT, _DELHI_LON, natural="tree", circumference="50")]
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=[],
    )
    assert report.inserted == 1
    assert report.rejected == 0


def test_implausible_height_field_is_none_not_rejected(tmp_path: Path):
    elements = [_node(3002, _DELHI_LAT, _DELHI_LON, natural="tree", height="200")]
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=[],
    )
    assert report.inserted == 1
    assert report.rejected == 0


# ---------------------------------------------------------------------------
# 3 m matching with fixture data
# ---------------------------------------------------------------------------

def test_tree_within_1m_is_linked(tmp_path: Path):
    """A tree 0.8 m from a register tree must be linked, not inserted."""
    lat_delta = 0.8 / 111_320
    elements = [_node(4001, _DELHI_LAT + lat_delta, _DELHI_LON, natural="tree")]
    reg = [_register_tree("REG-A", _DELHI_LAT, _DELHI_LON)]
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=reg,
    )
    assert report.linked == 1
    assert report.inserted == 0


def test_tree_at_exactly_3m_is_linked(tmp_path: Path):
    """A tree at the 3 m boundary is included (≤ threshold)."""
    lat_delta = 3.0 / 111_320
    elements = [_node(4002, _DELHI_LAT + lat_delta, _DELHI_LON, natural="tree")]
    reg = [_register_tree("REG-B", _DELHI_LAT, _DELHI_LON)]
    dist = haversine_distance_m(_DELHI_LAT, _DELHI_LON, _DELHI_LAT + lat_delta, _DELHI_LON)
    assert abs(dist - 3.0) < 0.1  # confirm fixture is really ~3 m

    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=reg,
    )
    assert report.linked == 1
    assert report.inserted == 0


def test_tree_just_outside_3m_is_inserted(tmp_path: Path):
    """A tree 3.2 m away is not linked — it becomes a new insert."""
    lat_delta = 3.2 / 111_320
    elements = [_node(4003, _DELHI_LAT + lat_delta, _DELHI_LON, natural="tree")]
    reg = [_register_tree("REG-C", _DELHI_LAT, _DELHI_LON)]
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=reg,
    )
    assert report.linked == 0
    assert report.inserted == 1


def test_osm_tree_linked_to_nearest_when_multiple_register_trees(tmp_path: Path):
    """With two register trees in range, the OSM tree is linked only once."""
    lat_delta = 1.0 / 111_320  # ~1 m north
    elements = [_node(4004, _DELHI_LAT + lat_delta, _DELHI_LON, natural="tree")]
    reg = [
        _register_tree("REG-D1", _DELHI_LAT, _DELHI_LON),
        _register_tree("REG-D2", _DELHI_LAT + 2 * lat_delta, _DELHI_LON),
    ]
    report = run_delhi_osm_import(
        cache_path=tmp_path / "cache.json",
        database_url=None,
        overpass_data=_overpass(elements),
        register_trees=reg,
    )
    # Should link once (first register hit); not create a new insert
    assert report.linked == 1
    assert report.inserted == 0


def test_merge_fill_applied_during_link(tmp_path: Path):
    """When linking, OSM fills empty register genus/species in memory."""
    from ingest.osm import OsmTreeImporter
    importer = OsmTreeImporter()

    reg_tree = _register_tree("REG-E", _DELHI_LAT, _DELHI_LON, genus=None, species=None)
    osm_node = _node(5001, _DELHI_LAT, _DELHI_LON, natural="tree",
                     genus="Ficus", species="benghalensis")
    osm_record = importer.parse_osm_node(osm_node)
    assert osm_record is not None

    filled = importer.merge_fill(reg_tree, osm_record)
    assert filled.genus == "Ficus"
    assert filled.species == "benghalensis"
    # source stays city_register, source_id stays REG-E
    assert filled.source == "city_register"
    assert filled.source_id == "REG-E"


# ---------------------------------------------------------------------------
# Overpass cache path behaviour
# ---------------------------------------------------------------------------

def test_cached_response_reused_without_network(tmp_path: Path, monkeypatch):
    """If the cache file exists, fetch_overpass must not make a network call."""
    import json

    from ingest import overpass as overpass_module

    cache = tmp_path / "osm_delhi_trees.json"
    payload = _overpass([_node(6001, _DELHI_LAT, _DELHI_LON, natural="tree")])
    cache.write_text(json.dumps(payload), encoding="utf-8")

    network_called = {"flag": False}

    def fake_post(*_args, **_kwargs):  # pragma: no cover
        network_called["flag"] = True
        raise AssertionError("Network should not be called when cache exists")

    monkeypatch.setattr(overpass_module.requests.Session, "post", fake_post)

    from ingest.overpass import build_delhi_query, fetch_overpass
    result = fetch_overpass(build_delhi_query(), cache)
    assert result["elements"][0]["id"] == 6001
    assert not network_called["flag"]


# ---------------------------------------------------------------------------
# ImportReport str
# ---------------------------------------------------------------------------

def test_report_str_contains_all_counts():
    r = ImportReport(nodes_fetched=100, inserted=80, linked=15, rejected=5)
    r.reject_reasons["parse_error"] = 5
    text = str(r)
    assert "100" in text
    assert "80" in text
    assert "15" in text
    assert "5" in text
    assert "parse_error" in text
