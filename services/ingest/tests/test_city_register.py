import csv
from pathlib import Path

import pytest
import yaml
from shapely.geometry import Point

from ingest.city_register import CityRegisterImporter, upsert_records, write_report
from ingest.models import TreeRecord

MAPPING_PATH = Path(__file__).parent.parent / "mappings" / "city_register_mapping.yaml"


def test_split_scientific_name():
    assert TreeRecord.split_scientific_name("Tilia cordata") == ("Tilia", "cordata")
    assert TreeRecord.split_scientific_name("Acer platanoides 'Crimson King'") == (
        "Acer",
        "platanoides",
    )
    assert TreeRecord.split_scientific_name("Platanus x acerifolia") == (
        "Platanus",
        "x acerifolia",
    )


def build_importer(tmp_path: Path) -> CityRegisterImporter:
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    mapping["licence"] = "Test dataset licence"
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping), encoding="utf-8")
    return CityRegisterImporter(mapping_path)


def test_processes_50_row_delhi_sample_and_reports_skips(tmp_path: Path):
    sample_path = tmp_path / "delhi_sample.csv"
    columns = [
        "tree_id",
        "scientific_name",
        "land_type",
        "trunk_circumference_cm",
        "height_m",
        "crown_diameter_m",
        "planted_year",
        "leaf_cycle",
        "longitude",
        "latitude",
    ]
    with sample_path.open("w", encoding="utf-8", newline="") as sample_file:
        writer = csv.DictWriter(sample_file, fieldnames=columns)
        writer.writeheader()
        for index in range(50):
            writer.writerow(
                {
                    "tree_id": "" if index == 46 else f"DL-{index:03d}",
                    "scientific_name": "" if index == 49 else "Azadirachta indica",
                    "land_type": "private" if index == 48 else "Public",
                    "trunk_circumference_cm": 120,
                    "height_m": 16.5,
                    "crown_diameter_m": 8.2,
                    "planted_year": 1995,
                    "leaf_cycle": "evergreen",
                    "longitude": "" if index == 47 else 77.2,
                    "latitude": 28.6,
                }
            )

    importer = build_importer(tmp_path)
    records, stats = importer.process_file(sample_path)

    assert stats == {
        "rows_read": 50,
        "loaded": 47,
        "skipped": {
            "missing_point": 1,
            "missing_source_id": 1,
            "not_public_land": 1,
        },
        "unmatched_species": {"(missing)": 1},
    }
    assert records[0].source == "city_register"
    assert records[0].source_id == "DL-000"
    assert records[0].licence == "Test dataset licence"
    assert records[0].genus == "Azadirachta"
    assert records[0].species == "indica"
    assert records[0].circumference_m == 1.2
    assert records[0].height_m == 16.5
    assert records[0].crown_diameter_m == 8.2
    assert records[0].leaf_cycle == "evergreen"
    assert records[0].raw_attributes["trunk_circumference_cm"] == "120"

    report_path = tmp_path / "out" / "report.md"
    write_report(report_path, stats)
    report = report_path.read_text(encoding="utf-8")
    assert "Rows read: 50" in report
    assert "Loaded/upserted: 47" in report
    assert "not_public_land: 1" in report
    assert "(missing): 1" in report


def test_converts_diameter_to_circumference_in_metres(tmp_path: Path):
    importer = build_importer(tmp_path)
    importer.mapping["rules"]["trunk_measurement_type"] = "diameter"
    importer.mapping["rules"]["trunk_measurement_unit"] = "cm"

    record, reason, unmatched_name = importer.process_feature_result(
        {
            "tree_id": "DL-001",
            "scientific_name": "Ficus religiosa",
            "land_type": "public",
            "trunk_circumference_cm": "100",
        },
        Point(77.2, 28.6),
    )

    assert reason is None
    assert unmatched_name is None
    assert record is not None
    assert record.circumference_m == 3.14


def test_reprojects_csv_coordinates_from_mapping_crs(tmp_path: Path):
    importer = build_importer(tmp_path)
    importer.mapping["source_crs"] = "EPSG:3857"
    sample_path = tmp_path / "projected.csv"
    sample_path.write_text(
        "tree_id,scientific_name,land_type,longitude,latitude\n"
        "DL-3857,Ficus religiosa,public,111319.490793,111325.142866\n",
        encoding="utf-8",
    )

    records, stats = importer.process_file(sample_path)

    assert stats["loaded"] == 1
    assert records[0].longitude == pytest.approx(1.0, abs=1e-5)
    assert records[0].latitude == pytest.approx(1.0, abs=1e-5)


def test_download_saves_response_to_local_cache(tmp_path: Path, monkeypatch):
    importer = build_importer(tmp_path)

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def iter_content(chunk_size):
            assert chunk_size == 1024 * 1024
            return iter([b"tree_id,longitude,latitude\n", b"DL-1,77.2,28.6\n"])

    monkeypatch.setattr(
        "ingest.city_register.requests.get",
        lambda url, **kwargs: FakeResponse(),
    )

    cached_path = importer.download(
        "https://example.test/register.csv", tmp_path / "cache"
    )

    assert cached_path.read_text(encoding="utf-8") == (
        "tree_id,longitude,latitude\nDL-1,77.2,28.6\n"
    )
    assert not cached_path.with_suffix(".csv.part").exists()


def test_upsert_preserves_every_tree_field_and_closes_connection(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

    class FakeConnection:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def cursor(self):
            return FakeCursor()

        def close(self):
            self.closed = True

    connection = FakeConnection()
    captured = {}

    def fake_execute_batch(cursor, statement, values, page_size):
        captured["statement"] = statement
        captured["values"] = list(values)
        captured["page_size"] = page_size

    monkeypatch.setattr("psycopg2.connect", lambda _: connection)
    monkeypatch.setattr("psycopg2.extras.execute_batch", fake_execute_batch)
    record = TreeRecord(
        source="city_register",
        source_id="DL-1",
        licence="Test dataset licence",
        status="unverified",
        planted_year=1995,
        longitude=77.2,
        latitude=28.6,
        raw_attributes={"source_id": "DL-1"},
    )

    upsert_records("postgresql://test", [record])

    values = captured["values"]
    assert connection.closed
    assert captured["page_size"] == 1000
    assert "ON CONFLICT (source, source_id) DO UPDATE" in captured["statement"]
    assert len(values) == 1
    assert len(values[0]) == 14
    assert values[0][12] == 1995
    assert values[0][13].adapted == {"source_id": "DL-1"}
