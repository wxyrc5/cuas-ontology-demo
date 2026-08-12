"""CRS normalization gate backed by PROJ through pyproj.

The gate is deliberately site-specific.  A single hard-coded UTM zone is not
valid for the three airport demonstrations, so every mission declares its
target CRS and every incoming observation carries its source CRS.
"""
from __future__ import annotations

from math import isfinite
import re
from typing import Any

from pyproj import CRS, Transformer


POINT_RE = re.compile(r"^POINT \((-?[0-9]+(?:\.[0-9]+)?) (-?[0-9]+(?:\.[0-9]+)?)\)$")


def utm_epsg_for_wgs84(longitude: float, latitude: float) -> str:
    """Return the WGS84 UTM EPSG identifier for a lon/lat coordinate."""
    if not -180.0 <= longitude <= 180.0 or not -80.0 <= latitude <= 84.0:
        raise ValueError("coordinate is outside the standard UTM area of use")
    zone = min(60, max(1, int((longitude + 180.0) // 6.0) + 1))
    code = (32600 if latitude >= 0.0 else 32700) + zone
    return f"EPSG:{code}"


def normalize_point_wkt(
    position_wkt: str,
    source_crs: str,
    target_crs: str,
) -> dict[str, Any]:
    """Transform a WKT point and return an auditable normalization record."""
    match = POINT_RE.fullmatch(position_wkt.strip())
    if not match:
        raise ValueError("only two-dimensional WKT POINT input is accepted")
    x, y = map(float, match.groups())
    source = CRS.from_user_input(source_crs)
    target = CRS.from_user_input(target_crs)
    required = not source.equals(target)
    transformer = Transformer.from_crs(source, target, always_xy=True)
    out_x, out_y = transformer.transform(x, y)
    if not all(isfinite(value) for value in (out_x, out_y)):
        raise ValueError("coordinate transformation produced a non-finite result")
    return {
        "source_crs": source.to_string(),
        "target_crs": target.to_string(),
        "requires_transformation": required,
        "transformation_status": "TRANSFORMED" if required else "IDENTITY",
        "source_position_wkt": position_wkt,
        "normalized_position_wkt": f"POINT ({out_x:.3f} {out_y:.3f})",
        "operation": transformer.description,
    }


def validate_airport_target_crs(airport: dict[str, Any]) -> dict[str, Any]:
    expected = utm_epsg_for_wgs84(float(airport["longitude"]), float(airport["latitude"]))
    declared = str(airport["target_crs"])
    if declared != expected:
        raise ValueError(f"{airport['id']} target CRS {declared} does not match {expected}")
    return normalize_point_wkt(
        f"POINT ({airport['longitude']} {airport['latitude']})",
        "OGC:CRS84",
        declared,
    )
