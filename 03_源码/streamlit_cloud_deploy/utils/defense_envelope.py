"""Anisotropic 2-D/3-D defense-envelope geometry helpers.

Unlike a range circle, each envelope has independent major/minor axes, vertical
extent, orientation and a bounded directional bias.  Parameters are synthetic
engineering display assumptions stored per airport in ``airports.json``.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np


def validate_envelopes(envelopes: Iterable[dict[str, Any]]) -> None:
    items = list(envelopes)
    if not items:
        raise ValueError("At least one defense envelope is required")
    previous_axes = (0.0, 0.0, 0.0)
    ids: set[str] = set()
    for envelope in items:
        envelope_id = str(envelope["id"])
        if envelope_id in ids:
            raise ValueError(f"Duplicate defense envelope id: {envelope_id}")
        ids.add(envelope_id)
        major = float(envelope["semi_major_km"])
        minor = float(envelope["semi_minor_km"])
        height = float(envelope["height_km"])
        bias = float(envelope.get("directional_bias", 0.0))
        if not (major > minor > 0.0 and height > 0.0):
            raise ValueError(f"Invalid axes for {envelope_id}: {major}, {minor}, {height}")
        if not 0.0 <= bias <= 0.35:
            raise ValueError(f"directional_bias outside [0, 0.35] for {envelope_id}")
        if any(current <= previous for current, previous in zip((major, minor, height), previous_axes)):
            raise ValueError("Defense envelopes must be strictly nested by all three axes")
        previous_axes = (major, minor, height)


def _rotate(x: np.ndarray, y: np.ndarray, orientation_deg: float) -> tuple[np.ndarray, np.ndarray]:
    angle = math.radians(orientation_deg)
    cos_angle, sin_angle = math.cos(angle), math.sin(angle)
    return (
        x * cos_angle - y * sin_angle,
        x * sin_angle + y * cos_angle,
    )


def _inverse_rotate(
    x: np.ndarray,
    y: np.ndarray,
    orientation_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    return _rotate(x, y, -orientation_deg)


def envelope_boundary_xy(
    envelope: dict[str, Any],
    n_points: int = 181,
) -> tuple[np.ndarray, np.ndarray]:
    """Return a closed, rotated, directionally biased ground boundary in km."""
    if n_points < 32:
        raise ValueError("n_points must be >= 32")
    theta = np.linspace(0.0, 2.0 * np.pi, n_points)
    bias = float(envelope.get("directional_bias", 0.0))
    directional_scale = 1.0 + bias * np.cos(theta)
    x_local = float(envelope["semi_major_km"]) * np.cos(theta) * directional_scale
    y_local = float(envelope["semi_minor_km"]) * np.sin(theta) * directional_scale
    return _rotate(x_local, y_local, float(envelope.get("orientation_deg", 0.0)))


def envelope_surface_xyz(
    envelope: dict[str, Any],
    n_azimuth: int = 64,
    n_elevation: int = 24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return a flattened half-ellipsoid/lobed envelope surface in km."""
    theta = np.linspace(0.0, 2.0 * np.pi, n_azimuth)
    phi = np.linspace(0.0, np.pi / 2.0, n_elevation)
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
    bias = float(envelope.get("directional_bias", 0.0))
    directional_scale = 1.0 + bias * np.cos(theta_grid)
    radial = np.sin(phi_grid)
    x_local = (
        float(envelope["semi_major_km"])
        * np.cos(theta_grid)
        * radial
        * directional_scale
    )
    y_local = (
        float(envelope["semi_minor_km"])
        * np.sin(theta_grid)
        * radial
        * directional_scale
    )
    z = float(envelope["height_km"]) * np.cos(phi_grid)
    x, y = _rotate(x_local, y_local, float(envelope.get("orientation_deg", 0.0)))
    return x, y, z


def xy_to_latlon(
    x_km: np.ndarray,
    y_km: np.ndarray,
    center_latitude: float,
    center_longitude: float,
) -> tuple[np.ndarray, np.ndarray]:
    latitude = center_latitude + np.asarray(y_km) / 110.57
    longitude = center_longitude + np.asarray(x_km) / (
        111.32 * math.cos(math.radians(center_latitude))
    )
    return latitude, longitude


def envelope_boundary_latlon(
    envelope: dict[str, Any],
    center_latitude: float,
    center_longitude: float,
    n_points: int = 181,
) -> tuple[np.ndarray, np.ndarray]:
    x, y = envelope_boundary_xy(envelope, n_points=n_points)
    return xy_to_latlon(x, y, center_latitude, center_longitude)


def contains_xy(
    envelope: dict[str, Any],
    x_km: np.ndarray | float,
    y_km: np.ndarray | float,
) -> np.ndarray:
    """Test ground-plane membership in the directionally biased envelope."""
    x_array = np.asarray(x_km, dtype=float)
    y_array = np.asarray(y_km, dtype=float)
    x_local, y_local = _inverse_rotate(
        x_array,
        y_array,
        float(envelope.get("orientation_deg", 0.0)),
    )
    major = float(envelope["semi_major_km"])
    minor = float(envelope["semi_minor_km"])
    theta = np.arctan2(y_local / minor, x_local / major)
    directional_scale = 1.0 + float(envelope.get("directional_bias", 0.0)) * np.cos(theta)
    normalized_radius_sq = (
        (x_local / (major * directional_scale)) ** 2
        + (y_local / (minor * directional_scale)) ** 2
    )
    return normalized_radius_sq <= 1.0


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {hex_color}")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha:.3f})"


__all__ = [
    "contains_xy",
    "envelope_boundary_latlon",
    "envelope_boundary_xy",
    "envelope_surface_xyz",
    "hex_to_rgba",
    "validate_envelopes",
    "xy_to_latlon",
]

