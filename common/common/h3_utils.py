"""H3 hexagonal grid utilities."""

import h3

H3_RESOLUTION = 11


def get_h3_resolution() -> int:
    """Get the H3 resolution used for parkour spot indexing.

    Returns:
        H3 resolution level (default: 11)
    """
    return H3_RESOLUTION


def latlng_to_h3(lat: float, lng: float, resolution: int | None = None) -> str:
    """Convert latitude/longitude to H3 index.

    Args:
        lat: Latitude in degrees
        lng: Longitude in degrees
        resolution: H3 resolution level (default: H3_RESOLUTION)

    Returns:
        H3 index string
    """
    if resolution is None:
        resolution = H3_RESOLUTION
    return h3.latlng_to_cell(lat, lng, resolution)


def h3_to_latlng(h3_index: str) -> tuple[float, float]:
    """Convert H3 index to latitude/longitude centroid.

    Args:
        h3_index: H3 index string

    Returns:
        Tuple of (latitude, longitude)
    """
    return h3.cell_to_latlng(h3_index)
