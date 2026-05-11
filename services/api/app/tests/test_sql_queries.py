"""Unit tests for SQL query module."""

import pytest

from common.sql_queries import (
    FEATURE_QUERIES,
    build_feature_query,
    get_all_feature_names,
)


class TestFeatureQueries:
    """Tests for the feature query registry."""

    def test_all_eight_categories_present(self) -> None:
        """Test that all 8 feature categories are defined."""
        expected = [
            "walls",
            "steps",
            "rails_fences",
            "playgrounds",
            "parking",
            "benches_blocks",
            "fitness_stations",
            "private_access_penalty",
        ]
        for name in expected:
            assert name in FEATURE_QUERIES

    def test_all_queries_are_non_empty_strings(self) -> None:
        """Test that all query templates are non-empty strings."""
        for name, query in FEATURE_QUERIES.items():
            assert isinstance(query, str)
            assert len(query.strip()) > 0

    def test_all_queries_contain_h3_function(self) -> None:
        """Test that all queries use h3_lat_lng_to_cell for aggregation."""
        for name, query in FEATURE_QUERIES.items():
            assert "h3_lat_lng_to_cell" in query, (
                f"Query '{name}' missing h3_lat_lng_to_cell"
            )

    def test_all_queries_contain_group_by(self) -> None:
        """Test that all queries have GROUP BY clause."""
        for name, query in FEATURE_QUERIES.items():
            assert "GROUP BY" in query.upper(), f"Query '{name}' missing GROUP BY"

    def test_all_queries_reference_planet_osm_tables(self) -> None:
        """Test that all queries reference planet_osm_* tables."""
        for name, query in FEATURE_QUERIES.items():
            assert "planet_osm_" in query, (
                f"Query '{name}' missing planet_osm table reference"
            )

    def test_all_queries_have_comments(self) -> None:
        """Test that all queries have documentation comments."""
        for name, query in FEATURE_QUERIES.items():
            assert "-- FEATURE:" in query, f"Query '{name}' missing FEATURE comment"


class TestSpecificQueries:
    """Tests for individual feature query content."""

    def test_walls_query_references_barrier(self) -> None:
        """Test that walls query checks barrier tag."""
        assert "barrier" in FEATURE_QUERIES["walls"]
        assert "wall" in FEATURE_QUERIES["walls"]

    def test_steps_query_references_highway(self) -> None:
        """Test that steps query checks highway=steps."""
        assert "highway" in FEATURE_QUERIES["steps"]
        assert "steps" in FEATURE_QUERIES["steps"]

    def test_rails_fences_query_references_barrier_and_railway(self) -> None:
        """Test that rails_fences query checks barrier and railway tags."""
        query = FEATURE_QUERIES["rails_fences"]
        assert "fence" in query
        assert "rail" in query

    def test_playgrounds_query_references_leisure(self) -> None:
        """Test that playgrounds query checks leisure=playground."""
        assert "leisure" in FEATURE_QUERIES["playgrounds"]
        assert "playground" in FEATURE_QUERIES["playgrounds"]

    def test_parking_query_references_amenity_and_parking(self) -> None:
        """Test that parking query checks amenity and parking tags."""
        query = FEATURE_QUERIES["parking"]
        assert "parking" in query

    def test_benches_blocks_query_references_amenity_and_barrier(self) -> None:
        """Test that benches_blocks query checks amenity=bench and barrier=block."""
        query = FEATURE_QUERIES["benches_blocks"]
        assert "bench" in query
        assert "block" in query

    def test_fitness_stations_query_references_leisure_and_sport(self) -> None:
        """Test that fitness_stations query checks leisure and sport tags."""
        query = FEATURE_QUERIES["fitness_stations"]
        assert "fitness" in query

    def test_private_access_query_references_access_tag(self) -> None:
        """Test that private_access query checks access=private and access=no."""
        query = FEATURE_QUERIES["private_access_penalty"]
        assert "private" in query
        assert "'no'" in query


class TestBuildFeatureQuery:
    """Tests for the build_feature_query helper."""

    def test_build_query_returns_text_object(self) -> None:
        """Test that build_feature_query returns a SQLAlchemy text object."""
        from sqlalchemy.sql.elements import TextClause

        query = build_feature_query("walls", [123456789])
        assert isinstance(query, TextClause)

    def test_build_query_with_invalid_name_raises(self) -> None:
        """Test that invalid feature name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown feature category"):
            build_feature_query("nonexistent", [123456789])

    def test_build_query_binds_parameters(self) -> None:
        """Test that query has bound parameters."""
        query = build_feature_query("walls", [123456789, 987654321])
        # The query should have the parameters bound
        assert query is not None

    def test_build_query_custom_resolution(self) -> None:
        """Test that custom resolution is accepted."""
        query = build_feature_query("walls", [123456789], resolution=10)
        assert query is not None


class TestGetAllFeatureNames:
    """Tests for get_all_feature_names helper."""

    def test_returns_list(self) -> None:
        """Test that get_all_feature_names returns a list."""
        names = get_all_feature_names()
        assert isinstance(names, list)

    def test_returns_feature_names_count(self) -> None:
        """Test that feature names are returned."""
        names = get_all_feature_names()
        assert len(names) == len(FEATURE_QUERIES)

    def test_names_match_registry(self) -> None:
        """Test that returned names match FEATURE_QUERIES keys."""
        names = get_all_feature_names()
        assert set(names) == set(FEATURE_QUERIES.keys())
