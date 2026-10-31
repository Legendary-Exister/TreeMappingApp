from ingest.models import TreeRecord
from ingest.osm import OSM_LICENCE_FULL, OsmTreeImporter, haversine_distance_m


def test_haversine_distance():
    # Same point
    assert haversine_distance_m(52.5200, 13.4050, 52.5200, 13.4050) == 0.0

    # Approx 111km between 1 degree latitude
    dist = haversine_distance_m(52.0, 13.0, 53.0, 13.0)
    assert 110_000 < dist < 112_000


def test_osm_node_parsing():
    importer = OsmTreeImporter()
    node = {
        "id": 1001,
        "lat": 52.5201,
        "lon": 13.4052,
        "tags": {
            "natural": "tree",
            "genus": "Quercus",
            "species": "robur",
            "circumference": "1.85m",
            "height": "14",
            "leaf_cycle": "deciduous",
        },
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.source == "osm"
    assert record.source_id == "node/1001"
    assert record.genus == "Quercus"
    assert record.species == "robur"
    assert record.circumference_m == 1.85
    assert record.height_m == 14.0
    assert record.leaf_cycle == "deciduous"


# ---------------------------------------------------------------------------
# Plausibility rules — tag parsing
# ---------------------------------------------------------------------------

def test_circumference_above_max_is_rejected():
    importer = OsmTreeImporter()
    node = {
        "id": 2001,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "circumference": "44"},  # > 43 m
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.circumference_m is None  # rejected as implausible


def test_circumference_at_max_boundary_is_accepted():
    importer = OsmTreeImporter()
    node = {
        "id": 2002,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "circumference": "43.0"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.circumference_m == 43.0


def test_height_above_max_is_rejected():
    importer = OsmTreeImporter()
    node = {
        "id": 2003,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "height": "117"},  # > 116 m
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.height_m is None


def test_height_at_max_boundary_is_accepted():
    importer = OsmTreeImporter()
    node = {
        "id": 2004,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "height": "116"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.height_m == 116.0


def test_non_numeric_circumference_is_ignored():
    importer = OsmTreeImporter()
    node = {
        "id": 2005,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "circumference": "large"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.circumference_m is None


def test_crown_diameter_parsed_from_diameter_crown_tag():
    importer = OsmTreeImporter()
    node = {
        "id": 2006,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "diameter_crown": "8.5"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.crown_diameter_m == 8.5


def test_crown_diameter_above_max_is_rejected():
    importer = OsmTreeImporter()
    node = {
        "id": 2007,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "diameter_crown": "61"},  # > 60 m
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.crown_diameter_m is None


def test_leaf_cycle_semi_evergreen_variant_normalised():
    importer = OsmTreeImporter()
    node = {
        "id": 2008,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "leaf_cycle": "semi-evergreen"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.leaf_cycle == "semi_evergreen"


def test_leaf_cycle_unknown_value_is_dropped():
    importer = OsmTreeImporter()
    node = {
        "id": 2009,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "leaf_cycle": "biennial"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.leaf_cycle is None


def test_taxon_tag_fills_genus_and_species():
    importer = OsmTreeImporter()
    node = {
        "id": 2010,
        "lat": 28.6, "lon": 77.2,
        "tags": {"natural": "tree", "taxon": "Ficus religiosa"},
    }
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.genus == "Ficus"
    assert record.species == "religiosa"


def test_osm_licence_and_source_set_correctly():
    importer = OsmTreeImporter()
    node = {"id": 2011, "lat": 28.6, "lon": 77.2, "tags": {"natural": "tree"}}
    record = importer.parse_osm_node(node)
    assert record is not None
    assert record.source == "osm"
    assert record.source_id == "node/2011"
    assert "ODbL" in record.licence
    assert "OpenStreetMap contributors" in record.licence
    assert record.licence == OSM_LICENCE_FULL


def test_node_without_id_returns_none():
    importer = OsmTreeImporter()
    assert importer.parse_osm_node({"lat": 28.6, "lon": 77.2, "tags": {}}) is None


def test_node_without_coordinates_returns_none():
    importer = OsmTreeImporter()
    assert importer.parse_osm_node({"id": 9999, "tags": {}}) is None


# ---------------------------------------------------------------------------
# merge_fill
# ---------------------------------------------------------------------------

def _make_tree(**kwargs) -> TreeRecord:
    defaults: dict = {"source": "city_register", "source_id": "X", "licence": "L",
                      "latitude": 28.6, "longitude": 77.2}
    defaults.update(kwargs)
    return TreeRecord(**defaults)


def test_merge_fill_copies_missing_fields():
    importer = OsmTreeImporter()
    register = _make_tree(genus=None, height_m=None)
    osm = _make_tree(source="osm", source_id="node/1", genus="Ficus", height_m=12.0)
    result = importer.merge_fill(register, osm)
    assert result.genus == "Ficus"
    assert result.height_m == 12.0


def test_merge_fill_never_overwrites_register_values():
    importer = OsmTreeImporter()
    register = _make_tree(genus="Azadirachta", height_m=8.0)
    osm = _make_tree(source="osm", source_id="node/2", genus="Ficus", height_m=15.0)
    result = importer.merge_fill(register, osm)
    assert result.genus == "Azadirachta"
    assert result.height_m == 8.0


def test_merge_fill_returns_same_object_when_no_changes():
    importer = OsmTreeImporter()
    register = _make_tree(genus="Ficus")
    osm = _make_tree(source="osm", source_id="node/3", genus="Tilia")
    result = importer.merge_fill(register, osm)
    assert result is register


# ---------------------------------------------------------------------------
# 3 m matching (original + additional edge cases)
# ---------------------------------------------------------------------------

def test_osm_duplicate_check_within_3m():
    importer = OsmTreeImporter()
    register_tree = TreeRecord(
        source="city_register",
        source_id="101",
        licence="Open",
        latitude=52.520000,
        longitude=13.405000,
    )

    # 1.5 meters away
    nearby_osm = TreeRecord(
        source="osm",
        source_id="node/99",
        licence="ODbL",
        latitude=52.520010,
        longitude=13.405010,
    )

    is_dup, matched, dist = importer.check_duplicate(nearby_osm, [register_tree], threshold_m=3.0)
    assert is_dup is True
    assert matched is not None
    assert matched.source_id == "101"
    assert dist is not None and dist < 3.0


def test_osm_duplicate_check_outside_3m():
    importer = OsmTreeImporter()
    register_tree = TreeRecord(
        source="city_register",
        source_id="201",
        licence="Open",
        latitude=28.600000,
        longitude=77.200000,
    )
    # ~5 m away (roughly 0.000045° latitude ≈ 5 m)
    far_osm = TreeRecord(
        source="osm",
        source_id="node/200",
        licence="ODbL",
        latitude=28.600045,
        longitude=77.200000,
    )
    is_dup, matched, dist = importer.check_duplicate(far_osm, [register_tree], threshold_m=3.0)
    assert is_dup is False
    assert matched is None
    assert dist is None


def test_osm_duplicate_check_exactly_at_threshold():
    """A tree at exactly 3.0 m should be considered a duplicate."""
    # Place two points 3.0 m apart (≈ 0.000027° latitude at equator)
    lat_delta = 3.0 / 111_320  # degrees per metre at equator
    register_tree = TreeRecord(
        source="city_register", source_id="REG-3", licence="Open",
        latitude=0.0, longitude=0.0,
    )
    osm_tree = TreeRecord(
        source="osm", source_id="node/300", licence="ODbL",
        latitude=lat_delta, longitude=0.0,
    )
    dist_m = haversine_distance_m(0.0, 0.0, lat_delta, 0.0)
    assert abs(dist_m - 3.0) < 0.1  # sanity: points really are ~3 m apart

    importer = OsmTreeImporter()
    is_dup, _, _ = importer.check_duplicate(osm_tree, [register_tree], threshold_m=3.0)
    assert is_dup is True


def test_osm_duplicate_check_empty_register_list():
    importer = OsmTreeImporter()
    osm_tree = TreeRecord(
        source="osm", source_id="node/400", licence="ODbL",
        latitude=28.6, longitude=77.2,
    )
    is_dup, matched, dist = importer.check_duplicate(osm_tree, [], threshold_m=3.0)
    assert is_dup is False
    assert matched is None
    assert dist is None
