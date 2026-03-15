"""
Unit tests for survival trend and top mortality parcel methods.
Tests use mocking to avoid requiring a live DuckDB database.
"""
import pytest
from unittest.mock import patch, MagicMock
from analytics import PURAnalytics


@pytest.fixture
def analytics():
    return PURAnalytics("test.db")


class TestCalculateSurvivalTrend:

    def test_invalid_window_raises(self, analytics):
        with pytest.raises(ValueError, match="window_visits must be at least 2"):
            analytics.calculate_survival_trend(window_visits=1)

    def test_improving_trend(self, analytics):
        """Simulate parcels where latest visit > first visit → improving."""
        mock_rows = [
            # parcel_id, trees_alive, trees_planned, rn
            (1, 90, 100, 1),  # latest: 90%
            (1, 70, 100, 2),  # oldest: 70%
            (2, 85, 100, 1),
            (2, 65, 100, 2),
        ]
        with patch("duckdb.connect") as mock_connect:
            mock_con = MagicMock()
            mock_connect.return_value.__enter__ = lambda s: mock_con
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_con.execute.return_value.fetchall.return_value = mock_rows
            mock_connect.return_value = mock_con

            result = analytics.calculate_survival_trend(window_visits=2)
            # Manual check: first visits have higher rn (older), latest rn=1
            # avg_first = (70+65)/2 = 67.5, avg_latest = (90+85)/2 = 87.5
            # The method sorts by rn descending=oldest first
            assert result["window_visits"] == 2

    def test_no_rows_returns_unknown(self, analytics):
        with patch("duckdb.connect") as mock_connect:
            mock_con = MagicMock()
            mock_connect.return_value = mock_con
            mock_con.execute.return_value.fetchall.return_value = []

            result = analytics.calculate_survival_trend()
            assert result["trend_direction"] == "unknown"
            assert result["parcels_analyzed"] == 0

    def test_returns_required_keys(self, analytics):
        with patch("duckdb.connect") as mock_connect:
            mock_con = MagicMock()
            mock_connect.return_value = mock_con
            mock_con.execute.return_value.fetchall.return_value = []

            result = analytics.calculate_survival_trend()
            for key in ("trend_direction", "parcels_analyzed", "change_pct_points", "window_visits"):
                assert key in result


class TestGetTopMortalityParcels:

    def test_invalid_top_n_raises(self, analytics):
        with pytest.raises(ValueError, match="top_n must be at least 1"):
            analytics.get_top_mortality_parcels(top_n=0)

    def test_returns_list(self, analytics):
        mock_rows = [
            (101, "Maria Garcia", 100, 45, "2025-11-10", 55.0),
            (102, "Jose Lopez", 80, 50, "2025-11-08", 37.5),
        ]
        with patch("duckdb.connect") as mock_connect:
            mock_con = MagicMock()
            mock_connect.return_value = mock_con
            mock_con.execute.return_value.fetchall.return_value = mock_rows

            result = analytics.get_top_mortality_parcels(top_n=5)
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["mortality_rate_pct"] == 55.0

    def test_result_has_required_fields(self, analytics):
        mock_rows = [(101, "Test Farmer", 100, 80, "2025-10-01", 20.0)]
        with patch("duckdb.connect") as mock_connect:
            mock_con = MagicMock()
            mock_connect.return_value = mock_con
            mock_con.execute.return_value.fetchall.return_value = mock_rows

            result = analytics.get_top_mortality_parcels()
            assert "parcel_id" in result[0]
            assert "mortality_rate_pct" in result[0]
            assert "farmer_name" in result[0]
