"""Generate georeferenced offline airport basemaps for the Streamlit demo.

The generated PNG files are display assets. Runtime rendering does not require
``contextily`` or network access; those are needed only when regenerating maps.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_map(
    airport: dict,
    output_dir: Path,
    *,
    longitude_half_span: float = 0.24,
    latitude_half_span: float = 0.12,
    zoom: int = 12,
) -> dict:
    """Download, crop and save one OpenStreetMap basemap."""
    import contextily as ctx

    latitude = float(airport["latitude"])
    longitude = float(airport["longitude"])
    west = longitude - longitude_half_span
    east = longitude + longitude_half_span
    south = latitude - latitude_half_span
    north = latitude + latitude_half_span

    physical_width = (east - west) * 111.32 * math.cos(math.radians(latitude))
    physical_height = (north - south) * 110.57
    aspect = max(0.75, min(1.5, physical_width / physical_height))

    figure = plt.figure(figsize=(9 * aspect, 9), dpi=140)
    axes = figure.add_axes([0, 0, 1, 1])
    axes.set_xlim(west, east)
    axes.set_ylim(south, north)
    axes.set_aspect("auto")
    ctx.add_basemap(
        axes,
        crs="EPSG:4326",
        source=ctx.providers.OpenStreetMap.Mapnik,
        zoom=zoom,
        alpha=0.88,
        attribution=False,
        reset_extent=True,
    )
    axes.set_xlim(west, east)
    axes.set_ylim(south, north)
    axes.axis("off")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{airport['id']}.png"
    figure.savefig(output_path, dpi=140, pad_inches=0)
    plt.close(figure)

    return {
        "file": output_path.name,
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "zoom": zoom,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "app_dir",
        type=Path,
        help="Streamlit application directory containing data/airports.json",
    )
    args = parser.parse_args()

    app_dir = args.app_dir.resolve()
    data_path = app_dir / "data" / "airports.json"
    output_dir = app_dir / "static" / "maps"
    with data_path.open(encoding="utf-8") as handle:
        airports = json.load(handle)["airports"]

    metadata = {
        "provider": "OpenStreetMap.Mapnik",
        "attribution": "© OpenStreetMap contributors",
        "generated_on": date.today().isoformat(),
        "airports": {},
    }
    for airport in airports:
        airport_id = airport["id"]
        print(f"Generating {airport_id}: {airport['name_zh']}", flush=True)
        metadata["airports"][airport_id] = generate_map(airport, output_dir)

    index_path = output_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Saved {len(airports)} maps and {index_path}")


if __name__ == "__main__":
    main()
