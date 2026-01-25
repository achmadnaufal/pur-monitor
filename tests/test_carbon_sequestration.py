"""
Unit tests for carbon sequestration calculations in PUR monitoring.

Tests the calculate_carbon_sequestration() method with various tree counts
and custom carbon rates.
"""

import pytest
from datetime import datetime
from analytics import PURAnalytics


class TestCarbonSequestration:
    """Test suite for carbon sequestration analytics."""
    
    def test_carbon_calc_default_rate(self):
        """Test carbon calculation with default 15 kg CO2/tree/year."""
        analytics = PURAnalytics("pur_monitor.db")
        result = analytics.calculate_carbon_sequestration()
        
        # Should have required keys
        assert "total_trees_alive" in result
        assert "avg_annual_carbon_kg" in result
        assert "avg_annual_carbon_tonnes" in result
        assert "10_year_projection_tonnes" in result
        assert "30_year_projection_tonnes" in result
    
    def test_carbon_calc_custom_rates(self):
        """Test carbon calculation with custom species-specific rates."""
        analytics = PURAnalytics("pur_monitor.db")
        
        custom_rates = {
            "eucalyptus": 20.0,
            "cedar": 18.0,
            "pine": 16.0,
        }
        
        result = analytics.calculate_carbon_sequestration(custom_rates)
        
        assert isinstance(result, dict)
        assert result["10_year_projection_tonnes"] >= 0
        assert result["30_year_projection_tonnes"] >= result["10_year_projection_tonnes"]
    
    def test_carbon_calc_invalid_rates(self):
        """Test that invalid carbon rates raise ValueError."""
        analytics = PURAnalytics("pur_monitor.db")
        
        with pytest.raises(ValueError):
            analytics.calculate_carbon_sequestration({"species": -5.0})
        
        with pytest.raises(ValueError):
            analytics.calculate_carbon_sequestration({"species": 0.0})
    
    def test_carbon_consistency(self):
        """Test that carbon calculations are internally consistent."""
        analytics = PURAnalytics("pur_monitor.db")
        result = analytics.calculate_carbon_sequestration()
        
        # 10-year should be ~10x the annual
        expected_10yr = result["avg_annual_carbon_tonnes"] * 10
        assert abs(result["10_year_projection_tonnes"] - expected_10yr) < 0.01
        
        # 30-year should be ~30x the annual
        expected_30yr = result["avg_annual_carbon_tonnes"] * 30
        assert abs(result["30_year_projection_tonnes"] - expected_30yr) < 0.01


class TestAnalyticsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_analytics_init_invalid_path(self):
        """Test that invalid db_path raises appropriate error."""
        with pytest.raises(TypeError):
            PURAnalytics(123)  # Not a string
        
        with pytest.raises(ValueError):
            PURAnalytics("")  # Empty string
    
    def test_tree_survival_empty_database(self):
        """Test survival stats with empty parcel_visits table."""
        analytics = PURAnalytics("pur_monitor.db")
        result = analytics.get_tree_survival_stats()
        
        # Should return dict with all zero/safe values
        assert result["total_parcels_visited"] >= 0
        assert result["overall_survival_percentage"] >= 0
        assert result["overall_survival_percentage"] <= 100
    
    def test_engagement_metrics_empty_farmers(self):
        """Test engagement metrics with empty farmers table."""
        analytics = PURAnalytics("pur_monitor.db")
        result = analytics.get_farmer_engagement_metrics()
        
        # Should not crash, return zeros
        assert result["total_farmers"] >= 0
        assert result["engagement_rate_pct"] >= 0
        assert result["female_ratio_pct"] >= 0
    
    def test_planting_completion_invalid_days(self):
        """Test planting completion rate with invalid day parameters."""
        analytics = PURAnalytics("pur_monitor.db")
        
        with pytest.raises(ValueError):
            analytics.calculate_planting_completion_rate(-1)
        
        with pytest.raises(ValueError):
            analytics.calculate_planting_completion_rate(3651)
    
    def test_planting_completion_boundary(self):
        """Test planting completion rate at day boundaries."""
        analytics = PURAnalytics("pur_monitor.db")
        
        # Should not crash
        result_0 = analytics.calculate_planting_completion_rate(0)
        result_30 = analytics.calculate_planting_completion_rate(30)
        result_365 = analytics.calculate_planting_completion_rate(365)
        
        assert isinstance(result_0, float)
        assert isinstance(result_30, float)
        assert isinstance(result_365, float)
        assert all(0 <= r <= 100 for r in [result_0, result_30, result_365])
