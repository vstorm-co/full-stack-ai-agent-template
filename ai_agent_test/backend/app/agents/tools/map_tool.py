"""Map-generation tool for agents.

Mirrors ``chart_tool``: the agent calls ``create_map`` with marker coordinates
and the tool returns a structured ``MapSpec`` as a JSON string. The web frontend
parses it and renders an interactive map with Leaflet + OpenStreetMap tiles
(global coverage, no API key). The model supplies latitude/longitude for known
places directly from its own knowledge.
"""

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

MAX_MARKERS = 100


class MapMarker(BaseModel):
    """A single point on the map."""

    lat: float = Field(ge=-90, le=90, description="Latitude in decimal degrees.")
    lng: float = Field(ge=-180, le=180, description="Longitude in decimal degrees.")
    label: str = Field(max_length=120, description="Short marker label.")
    description: str | None = Field(
        default=None, max_length=300, description="Optional detail shown on click."
    )
    color: str | None = Field(default=None, description="Hex color override, e.g. '#ef4444'.")


class MapSpec(BaseModel):
    """Canonical map payload produced by the tool and rendered by the frontend."""

    kind: str = Field(default="map")
    title: str = Field(max_length=200)
    markers: list[MapMarker]
    center: list[float] | None = Field(
        default=None, description="Optional [lat, lng] center; auto-fit to markers if omitted."
    )
    zoom: int | None = Field(default=None, ge=1, le=18, description="Optional zoom (1-18).")

    @field_validator("markers")
    @classmethod
    def _validate_markers(cls, v: list[MapMarker]) -> list[MapMarker]:
        """Require at least one marker and cap the total."""
        if not v:
            raise ValueError("markers must contain at least one point")
        if len(v) > MAX_MARKERS:
            raise ValueError(f"too many markers (max {MAX_MARKERS})")
        return v

    @field_validator("center")
    @classmethod
    def _validate_center(cls, v: list[float] | None) -> list[float] | None:
        """Require center, when given, to be an in-range [lat, lng] pair."""
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError("center must be [lat, lng]")
        lat, lng = v
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError("center out of range (lat must be -90..90, lng -180..180)")
        return v


def create_map(
    title: str,
    markers: list[dict[str, Any]],
    center: list[float] | None = None,
    zoom: int | None = None,
) -> str:
    """Create an interactive map for the user.

    Use this whenever the user asks to show, map, or locate places
    geographically. Provide latitude/longitude for each marker from your own
    knowledge (e.g. Warsaw ≈ 52.23, 21.01). The map renders interactively in the
    web chat with OpenStreetMap tiles.

    Args:
        title: Short title shown above the map.
        markers: List of {"lat", "lng", "label", "description"?, "color"?}.
        center: Optional [lat, lng] center. If omitted, the map auto-fits to the
            markers.
        zoom: Optional zoom level (1-18). Mainly useful with a single marker.

    Returns:
        A JSON string with the map specification. Do not repeat this JSON back to
        the user — just briefly describe the map you created.
    """
    try:
        spec = MapSpec(
            title=title,
            markers=[MapMarker(**m) for m in markers],
            center=center,
            zoom=zoom,
        )
    except ValidationError as e:
        return f"Could not build map — invalid arguments: {e.errors()}"
    except (TypeError, ValueError) as e:
        return f"Could not build map: {e}"

    return spec.model_dump_json()
