"""H3 hexagonal grid utilities."""

import math

import h3

H3_RESOLUTION = 11

# Approximate average edge length of an H3 cell at resolution 11 in meters.
# Used to convert a radius in km to a k-ring depth.
_AVG_EDGE_LENGTH_M = 25.0


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


def get_k_ring(h3_index: str, radius_km: float, resolution: int | None = None) -> set[str]:
    """Compute the H3 k-ring (all cells within k steps) covering a radius.

    The k-ring depth is derived from the radius and the approximate edge
    length of an H3 cell at the given resolution.

    Args:
        h3_index: Center H3 index string
        radius_km: Coverage radius in kilometers
        resolution: H3 resolution level (default: H3_RESOLUTION)

    Returns:
        Set of H3 index strings covering the k-ring
    """
    if resolution is None:
        resolution = H3_RESOLUTION

    # Convert radius to k-ring depth using average cell edge length
    radius_m = radius_km * 1000.0
    k = max(1, math.ceil(radius_m / _AVG_EDGE_LENGTH_M))

    # grid_disk returns all cells within k steps of the center cell
    # Wrap in set() for consistent return type across h3 library versions
    return set(h3.grid_disk(h3_index, k))


def h3_index_to_bigint(h3_index: str) -> int:
    """Convert an H3 hex string index to its bigint representation.

    h3-pg uses bigint for H3 indices; the Python h3 library uses hex strings.
    This function bridges the two formats.

    Args:
        h3_index: H3 index as a hex string (e.g. "8b1fb46622dffff")

    Returns:
        H3 index as a Python int (bigint)
    """
    return int(h3_index, 16)


def bigint_to_h3_index(bigint: int) -> str:
    """Convert a bigint H3 index to its hex string representation.

    Args:
        bigint: H3 index as a Python int

    Returns:
        H3 index as a hex string (e.g. "8b1fb46622dffff")
    """
    return format(bigint, "x")
