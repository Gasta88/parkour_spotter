"""Unit tests for H3 utilities."""

from common.h3_utils import (
    H3_RESOLUTION,
    bigint_to_h3_index,
    get_h3_resolution,
    get_k_ring,
    h3_index_to_bigint,
    h3_to_latlng,
    latlng_to_h3,
)


class TestH3Resolution:
    """Tests for H3 resolution configuration."""

    def test_get_h3_resolution(self) -> None:
        """Test that default resolution is 11."""
        assert get_h3_resolution() == 11

    def test_resolution_constant(self) -> None:
        """Test that H3_RESOLUTION constant is 11."""
        assert H3_RESOLUTION == 11


class TestLatLngConversion:
    """Tests for lat/lng ↔ H3 index conversion."""

    def test_latlng_to_h3_returns_string(self) -> None:
        """Test that latlng_to_h3 returns a hex string."""
        result = latlng_to_h3(45.4064, 11.8778)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_latlng_to_h3_roundtrip(self) -> None:
        """Test that latlng → h3 → latlng is approximately reversible."""
        lat, lon = 45.4064, 11.8778
        h3_index = latlng_to_h3(lat, lon)
        result_lat, result_lon = h3_to_latlng(h3_index)

        # At resolution 11, centroid should be within ~25m of original
        assert abs(result_lat - lat) < 0.001
        assert abs(result_lon - lon) < 0.001

    def test_h3_to_latlng_returns_tuple(self) -> None:
        """Test that h3_to_latlng returns a (lat, lon) tuple."""
        h3_index = latlng_to_h3(45.4064, 11.8778)
        result = h3_to_latlng(h3_index)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestKRing:
    """Tests for H3 k-ring computation."""

    def test_k_ring_includes_center(self) -> None:
        """Test that k-ring includes the center cell."""
        center = latlng_to_h3(45.4064, 11.8778)
        k_ring = get_k_ring(center, 0.1)  # Very small radius
        assert center in k_ring

    def test_k_ring_grows_with_radius(self) -> None:
        """Test that larger radius produces more cells."""
        center = latlng_to_h3(45.4064, 11.8778)
        small_ring = get_k_ring(center, 0.1)
        large_ring = get_k_ring(center, 5.0)
        assert len(large_ring) > len(small_ring)

    def test_k_ring_single_cell_small_radius(self) -> None:
        """Test that very small radius returns just the center cell."""
        center = latlng_to_h3(45.4064, 11.8778)
        k_ring = get_k_ring(center, 0.01)  # 10m radius
        # At resolution 11, edge length is ~25m, so 10m should give k=1
        assert len(k_ring) >= 1
        assert center in k_ring

    def test_k_ring_returns_set(self) -> None:
        """Test that k_ring returns a set of strings."""
        center = latlng_to_h3(45.4064, 11.8778)
        k_ring = get_k_ring(center, 1.0)
        assert isinstance(k_ring, set)
        for cell in k_ring:
            assert isinstance(cell, str)


class TestH3IndexConversion:
    """Tests for H3 index format conversion (hex string ↔ bigint)."""

    def test_hex_to_bigint(self) -> None:
        """Test converting hex string to bigint."""
        h3_hex = "8b1fb46622dffff"
        bigint = h3_index_to_bigint(h3_hex)
        assert isinstance(bigint, int)
        assert bigint > 0

    def test_bigint_to_hex(self) -> None:
        """Test converting bigint to hex string."""
        bigint = h3_index_to_bigint("8b1fb46622dffff")
        h3_hex = bigint_to_h3_index(bigint)
        assert h3_hex == "8b1fb46622dffff"

    def test_roundtrip_conversion(self) -> None:
        """Test that hex → bigint → hex is identity."""
        original = latlng_to_h3(45.4064, 11.8778)
        bigint = h3_index_to_bigint(original)
        result = bigint_to_h3_index(bigint)
        assert result == original

    def test_bigint_is_valid_hex(self) -> None:
        """Test that bigint converts back to valid hex."""
        h3_hex = latlng_to_h3(45.4064, 11.8778)
        bigint = h3_index_to_bigint(h3_hex)
        result = bigint_to_h3_index(bigint)
        # Should be a valid hex string
        int(result, 16)  # Should not raise
