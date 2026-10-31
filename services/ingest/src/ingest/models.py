from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class TreeRecord(BaseModel):
    source: str
    source_id: str
    licence: str
    status: str = "unverified"
    genus: Optional[str] = None
    species: Optional[str] = None
    leaf_cycle: Optional[str] = None
    circumference_m: Optional[float] = Field(default=None, ge=0.01, le=43.0)
    height_m: Optional[float] = Field(default=None, ge=0.5, le=116.0)
    crown_diameter_m: Optional[float] = Field(default=None, ge=0.5, le=60.0)
    planted_year: Optional[int] = Field(default=None, ge=1500, le=2030)
    longitude: float = Field(ge=-180.0, le=180.0)
    latitude: float = Field(ge=-90.0, le=90.0)
    raw_attributes: Optional[dict[str, Any]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"unverified", "verified", "disputed", "removed"}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}. Must be one of {valid_statuses}")
        return v

    @classmethod
    def split_scientific_name(cls, name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Split combined Latin botanical name into genus and species."""
        if not name or not isinstance(name, str):
            return None, None
        parts = name.strip().split()
        if not parts:
            return None, None
        genus = parts[0].capitalize()
        species = parts[1].lower() if len(parts) > 1 else None
        # Clean hybrid / cv markers if present
        if species in {"x", "×", "sp.", "spec."} and len(parts) > 2:
            species = f"{species} {parts[2].lower()}"
        return genus, species
