import math
from typing import Any

from ingest.models import TreeRecord

# Licence string used for every OSM-sourced tree
OSM_LICENCE = "ODbL"
OSM_LICENCE_CREDIT = "© OpenStreetMap contributors"
OSM_LICENCE_FULL = f"{OSM_LICENCE} ({OSM_LICENCE_CREDIT})"


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in metres."""
    r = 6371000.0  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class OsmTreeImporter:
    def parse_osm_node(self, node: dict[str, Any]) -> TreeRecord | None:
        """Parse an Overpass API node representation of natural=tree."""
        raw_id = node.get("id")
        lat = node.get("lat")
        lon = node.get("lon")
        tags = node.get("tags", {})

        if raw_id is None or lat is None or lon is None:
            return None
        node_id = str(raw_id)

        genus = tags.get("genus")
        species = tags.get("species")
        leaf_cycle = tags.get("leaf_cycle")

        if not genus and "taxon" in tags:
            genus, species = TreeRecord.split_scientific_name(tags["taxon"])

        # Parse circumference
        circ_m = None
        if "circumference" in tags:
            try:
                c = float(str(tags["circumference"]).replace("m", "").strip())
                if 0.05 <= c <= 43.0:
                    circ_m = round(c, 2)
            except (ValueError, TypeError):
                pass

        # Parse height
        height_m = None
        if "height" in tags:
            try:
                h = float(str(tags["height"]).replace("m", "").strip())
                if 0.5 <= h <= 116.0:
                    height_m = round(h, 1)
            except (ValueError, TypeError):
                pass

        # Parse crown diameter  (OSM tag: diameter_crown, unit metres)
        crown_diameter_m = None
        for tag_key in ("diameter_crown", "crown_diameter"):
            if tag_key in tags:
                try:
                    d = float(str(tags[tag_key]).replace("m", "").strip())
                    if 0.5 <= d <= 60.0:
                        crown_diameter_m = round(d, 1)
                except (ValueError, TypeError):
                    pass
                break

        # Normalise leaf_cycle to the project enum values
        _lc_map = {
            "deciduous": "deciduous",
            "evergreen": "evergreen",
            "semi_evergreen": "semi_evergreen",
            "semi-evergreen": "semi_evergreen",
            "unknown": "unknown",
        }
        leaf_cycle = _lc_map.get(leaf_cycle.strip().casefold()) if leaf_cycle else None

        return TreeRecord(
            source="osm",
            source_id=f"node/{node_id}",
            licence=OSM_LICENCE_FULL,
            status="unverified",
            genus=genus.capitalize() if genus else None,
            species=species.lower() if species else None,
            leaf_cycle=leaf_cycle,
            circumference_m=circ_m,
            height_m=height_m,
            crown_diameter_m=crown_diameter_m,
            longitude=float(lon),
            latitude=float(lat),
            raw_attributes=tags,
        )

    @staticmethod
    def merge_fill(register_tree: TreeRecord, osm_tree: TreeRecord) -> TreeRecord:
        """Return *register_tree* enriched with non-null OSM fields.

        Register values are never overwritten; OSM values only fill gaps.
        Returns a new TreeRecord instance (TreeRecord is immutable via Pydantic).
        """
        updates: dict[str, Any] = {}
        for field in ("genus", "species", "leaf_cycle", "circumference_m",
                      "height_m", "crown_diameter_m"):
            if getattr(register_tree, field) is None and getattr(osm_tree, field) is not None:
                updates[field] = getattr(osm_tree, field)
        if not updates:
            return register_tree
        return register_tree.model_copy(update=updates)

    def check_duplicate(
        self,
        osm_tree: TreeRecord,
        existing_trees: list[TreeRecord],
        threshold_m: float = 3.0,
    ) -> tuple[bool, TreeRecord | None, float | None]:
        """Check if an OSM tree is within threshold distance of any existing tree."""
        for tree in existing_trees:
            dist = haversine_distance_m(
                osm_tree.latitude,
                osm_tree.longitude,
                tree.latitude,
                tree.longitude,
            )
            if dist <= threshold_m:
                return True, tree, dist
        return False, None, None
