import argparse
import csv
import math
import os
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests
import yaml
from shapely.geometry import Point

from ingest.models import TreeRecord


class CityRegisterImporter:
    def __init__(self, mapping_path: str | Path):
        with open(mapping_path, "r", encoding="utf-8") as mapping_file:
            self.mapping = yaml.safe_load(mapping_file)
        if not isinstance(self.mapping, dict):
            raise TypeError("The mapping file must contain a YAML object")
        self._validate_mapping()

    def _validate_mapping(self) -> None:
        columns = self.mapping.get("columns")
        if not isinstance(columns, dict) or not columns.get("id"):
            raise ValueError("The mapping must define columns.id")
        public_filter = self.mapping.get("public_land_filter")
        if (
            not isinstance(public_filter, dict)
            or not public_filter.get("column")
            or not public_filter.get("accepted_values")
        ):
            raise ValueError(
                "The mapping must define public_land_filter.column and accepted_values"
            )
        if not self.mapping.get("source_crs"):
            raise ValueError("The mapping must define source_crs")
        rules = self.mapping.get("rules", {})
        if rules.get("trunk_measurement_type", "circumference") not in {
            "circumference",
            "diameter",
        }:
            raise ValueError("trunk_measurement_type must be circumference or diameter")
        if rules.get("trunk_measurement_unit", "m") not in {"cm", "m"}:
            raise ValueError("trunk_measurement_unit must be cm or m")

    def download(self, url: str, cache_dir: str | Path) -> Path:
        data_format = self.mapping.get("data_format", "geojson").lower()
        extensions = {"geojson": ".geojson", "csv": ".csv", "shapefile": ".zip"}
        if data_format not in extensions:
            raise ValueError("data_format must be geojson, csv, or shapefile")

        target_dir = Path(cache_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"delhi_tree_register{extensions[data_format]}"
        temporary = target.with_suffix(target.suffix + ".part")
        try:
            with requests.get(url, stream=True, timeout=(15, 120)) as response:
                response.raise_for_status()
                with temporary.open("wb") as cache_file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            cache_file.write(chunk)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def read_features(self, path: str | Path) -> gpd.GeoDataFrame:
        source = Path(path)
        data_format = self.mapping.get("data_format", "geojson").lower()
        if data_format == "csv":
            with source.open("r", encoding="utf-8-sig", newline="") as source_file:
                rows = list(csv.DictReader(source_file))
            columns = self.mapping["columns"]
            geometries = [
                self._point_from_columns(
                    row, columns.get("longitude"), columns.get("latitude")
                )
                for row in rows
            ]
            features = gpd.GeoDataFrame(
                rows, geometry=geometries, crs=self.mapping["source_crs"]
            )
        elif data_format in {"geojson", "shapefile"}:
            features = gpd.read_file(source)
        else:
            raise ValueError("data_format must be geojson, csv, or shapefile")

        if features.crs is None:
            features = features.set_crs(self.mapping["source_crs"])
        return features.to_crs("EPSG:4326")

    @staticmethod
    def _point_from_columns(
        properties: dict[str, Any],
        longitude_column: str | None,
        latitude_column: str | None,
    ) -> Point | None:
        if not longitude_column or not latitude_column:
            return None
        try:
            x = float(properties[longitude_column])
            y = float(properties[latitude_column])
        except (KeyError, TypeError, ValueError):
            return None
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        return Point(x, y)

    def process_feature_result(
        self, properties: dict[str, Any], geometry: Any
    ) -> tuple[TreeRecord | None, str | None, str | None]:
        """Return a normalized record, skip reason, and unmatched scientific name."""
        columns = self.mapping["columns"]
        public_filter = self.mapping["public_land_filter"]
        land_value = properties.get(public_filter["column"])
        accepted = {
            str(value).strip().casefold() for value in public_filter["accepted_values"]
        }
        if (
            self._is_missing(land_value)
            or str(land_value).strip().casefold() not in accepted
        ):
            return None, "not_public_land", None

        source_id = properties.get(columns["id"])
        if self._is_missing(source_id):
            return None, "missing_source_id", None

        if geometry is None or not hasattr(geometry, "is_empty") or geometry.is_empty:
            return None, "missing_point", None
        if geometry.geom_type != "Point":
            return None, "geometry_not_point", None
        longitude, latitude = geometry.x, geometry.y
        if not (
            math.isfinite(longitude)
            and math.isfinite(latitude)
            and -180 <= longitude <= 180
            and -90 <= latitude <= 90
        ):
            return None, "invalid_point", None

        raw_name = properties.get(columns.get("scientific_name", ""))
        if self._is_missing(raw_name):
            raw_name = None
        genus, species = TreeRecord.split_scientific_name(raw_name)
        unmatched_name = None
        if genus is None or species is None:
            unmatched_name = (
                str(raw_name).strip() if raw_name is not None else "(missing)"
            )
            if not unmatched_name:
                unmatched_name = "(missing)"

        rules = self.mapping.get("rules", {})
        measurement = self._number(properties.get(columns.get("trunk_measurement", "")))
        circumference_m = None
        if measurement is not None and measurement > 0:
            unit = rules.get("trunk_measurement_unit", "m")
            measurement_m = measurement / 100 if unit == "cm" else measurement
            measurement_type = rules.get("trunk_measurement_type", "circumference")
            if measurement_type == "diameter":
                circumference_m = measurement_m * math.pi
            elif measurement_type == "circumference":
                circumference_m = measurement_m
            else:
                raise ValueError(
                    "trunk_measurement_type must be circumference or diameter"
                )
            if not 0.01 <= circumference_m <= rules.get("max_circumference_m", 43.0):
                circumference_m = None
        leaf_cycle = self._optional_value(properties, columns.get("leaf_cycle"))
        if leaf_cycle:
            leaf_cycle = leaf_cycle.strip().casefold()
            if leaf_cycle not in {
                "deciduous",
                "evergreen",
                "semi_evergreen",
                "unknown",
            }:
                leaf_cycle = None

        return (
            TreeRecord(
                source=self.mapping.get("source_name", "city_register"),
                source_id=str(source_id).strip(),
                licence=self.mapping.get("licence") or "",
                status=self.mapping.get("status", "unverified"),
                genus=genus,
                species=species,
                leaf_cycle=leaf_cycle,
                circumference_m=round(circumference_m, 2) if circumference_m else None,
                height_m=self._bounded_number(
                    properties.get(columns.get("height_m", "")),
                    0.5,
                    rules.get("max_height_m", 116.0),
                    1,
                ),
                crown_diameter_m=self._bounded_number(
                    properties.get(columns.get("crown_diameter_m", "")), 0.5, 60.0, 1
                ),
                planted_year=self._year(
                    properties.get(columns.get("planted_year", ""))
                ),
                longitude=longitude,
                latitude=latitude,
                raw_attributes={
                    key: self._json_safe(value) for key, value in properties.items()
                },
            ),
            None,
            unmatched_name,
        )

    def process_feature(
        self, properties: dict[str, Any], coordinates: list[float]
    ) -> TreeRecord | None:
        """Compatibility helper for callers with GeoJSON coordinates."""
        geometry = None
        if len(coordinates) >= 2:
            try:
                geometry = Point(float(coordinates[0]), float(coordinates[1]))
            except (TypeError, ValueError):
                pass
        record, _, _ = self.process_feature_result(properties, geometry)
        return record

    def process_file(self, path: str | Path) -> tuple[list[TreeRecord], dict[str, Any]]:
        features = self.read_features(path)
        records: list[TreeRecord] = []
        skipped: Counter[str] = Counter()
        unmatched_species: Counter[str] = Counter()
        for _, feature in features.iterrows():
            properties = feature.drop(labels="geometry").to_dict()
            record, reason, unmatched_name = self.process_feature_result(
                properties, feature.geometry
            )
            if reason:
                skipped[reason] += 1
            elif record is not None:
                records.append(record)
                if unmatched_name:
                    unmatched_species[unmatched_name] += 1
        return records, {
            "rows_read": len(features),
            "loaded": len(records),
            "skipped": dict(sorted(skipped.items())),
            "unmatched_species": dict(sorted(unmatched_species.items())),
        }

    @staticmethod
    def _number(value: Any) -> float | None:
        if CityRegisterImporter._is_missing(value):
            return None
        try:
            parsed = float(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return None
        return parsed if math.isfinite(parsed) else None

    @classmethod
    def _bounded_number(
        cls, value: Any, minimum: float, maximum: float, decimals: int
    ) -> float | None:
        parsed = cls._number(value)
        if parsed is None or not minimum <= parsed <= maximum:
            return None
        return round(parsed, decimals)

    @classmethod
    def _year(cls, value: Any) -> int | None:
        parsed = cls._number(value)
        if parsed is None or not parsed.is_integer() or not 1500 <= parsed <= 2030:
            return None
        return int(parsed)

    @staticmethod
    def _optional_value(properties: dict[str, Any], column: str | None) -> str | None:
        if not column or CityRegisterImporter._is_missing(properties.get(column)):
            return None
        value = str(properties[column]).strip()
        return value or None

    @staticmethod
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        try:
            return math.isnan(value)
        except TypeError:
            return False

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._json_safe(item) for item in value]
        if cls._is_missing(value):
            return None
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "item"):
            return cls._json_safe(value.item())
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)


def upsert_records(database_url: str, records: list[TreeRecord]) -> None:
    from psycopg2 import connect
    from psycopg2.extras import Json, execute_batch

    statement = """
        INSERT INTO public.trees (
            geom, source, source_id, licence, status, genus, species, leaf_cycle,
            circumference_m, height_m, crown_diameter_m, planted_year, raw_attributes
        ) VALUES (
            extensions.ST_SetSRID(extensions.ST_MakePoint(%s, %s), 4326)::extensions.geography,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (source, source_id) DO UPDATE SET
            geom = EXCLUDED.geom,
            licence = EXCLUDED.licence,
            status = EXCLUDED.status,
            genus = EXCLUDED.genus,
            species = EXCLUDED.species,
            leaf_cycle = EXCLUDED.leaf_cycle,
            circumference_m = EXCLUDED.circumference_m,
            height_m = EXCLUDED.height_m,
            crown_diameter_m = EXCLUDED.crown_diameter_m,
            planted_year = EXCLUDED.planted_year,
            raw_attributes = EXCLUDED.raw_attributes,
            updated_at = NOW()
    """
    values = (
        (
            record.longitude,
            record.latitude,
            record.source,
            record.source_id,
            record.licence,
            record.status,
            record.genus,
            record.species,
            record.leaf_cycle,
            record.circumference_m,
            record.height_m,
            record.crown_diameter_m,
            record.planted_year,
            Json(record.raw_attributes or {}),
        )
        for record in records
    )
    with (
        closing(connect(database_url)) as connection,
        connection,
        connection.cursor() as cursor,
    ):
        execute_batch(cursor, statement, values, page_size=1000)


def write_report(report_path: str | Path, stats: dict[str, Any]) -> None:
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Delhi tree register import report",
        "",
        f"- Rows read: {stats['rows_read']}",
        f"- Loaded/upserted: {stats['loaded']}",
        f"- Skipped: {sum(stats['skipped'].values())}",
        "",
        "## Skipped rows",
        "",
    ]
    lines.extend(f"- {reason}: {count}" for reason, count in stats["skipped"].items())
    if not stats["skipped"]:
        lines.append("- None")
    lines.extend(["", "## Species with no match", ""])
    lines.extend(
        f"- {name}: {count}" for name, count in stats["unmatched_species"].items()
    )
    if not stats["unmatched_species"]:
        lines.append("- None")
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Delhi city tree-register data")
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path(__file__).parents[2] / "mappings" / "city_register_mapping.yaml",
    )
    parser.add_argument(
        "--url", help="Override the dataset URL configured in the mapping"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(__file__).parents[2] / "data" / "cache",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).parents[2] / "out" / "report.md",
    )
    args = parser.parse_args()

    importer = CityRegisterImporter(args.mapping)
    url = args.url or importer.mapping.get("dataset_url")
    if not url:
        parser.error("Configure dataset_url in the mapping or pass --url")
    if not importer.mapping.get("licence"):
        parser.error("Set the source dataset licence in the mapping before importing")
    if importer.mapping.get("source_name", "city_register") != "city_register":
        parser.error("City-register imports must use source_name: city_register")

    source_file = importer.download(url, args.cache_dir)
    records, stats = importer.process_file(source_file)
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("Set DATABASE_URL to a Postgres connection using the service role")
    upsert_records(database_url, records)
    write_report(args.report, stats)
    print(
        f"Rows read: {stats['rows_read']}; loaded/upserted: {stats['loaded']}; "
        f"skipped: {sum(stats['skipped'].values())}; report: {args.report}"
    )


if __name__ == "__main__":
    main()
