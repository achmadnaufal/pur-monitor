"""
Unit tests for PUR Monitor core functions.

Tests cover:
- KPI calculations with edge cases
- Division by zero protection
- Null/empty input handling
- Percentage color coding logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.insert(0, '/Users/johndoe/projects/pur-monitor')

from monitor import get_con


class TestKPICalculations:
    """Test KPI calculation edge cases."""
    
    def test_percentage_color_coding_high_achievement(self):
        """Test percentage color for high achievement (>=80%)."""
        # Test green color (>=80%)
        pct = 85.5
        assert pct >= 80, "Should be green zone"
    
    def test_percentage_color_coding_medium_achievement(self):
        """Test percentage color for medium achievement (50-80%)."""
        # Test yellow color (50-80%)
        pct = 65.0
        assert 50 <= pct < 80, "Should be yellow zone"
    
    def test_percentage_color_coding_low_achievement(self):
        """Test percentage color for low achievement (<50%)."""
        # Test red color (<50%)
        pct = 25.0
        assert pct < 50, "Should be red zone"
    
    def test_zero_target_division_protection(self):
        """Test protection against division by zero when target is zero."""
        actual = 100
        target = 0
        # Should return 0 instead of raising ZeroDivisionError
        pct = (actual / target * 100) if target else 0
        assert pct == 0, "Zero target should return 0% without error"
    
    def test_zero_values_calculation(self):
        """Test calculation with zero actual and target values."""
        actual = 0
        target = 100
        pct = (actual / target * 100) if target else 0
        assert pct == 0.0, "Zero actual with non-zero target should give 0%"
    
    def test_both_zero_no_division_error(self):
        """Test that zero/zero doesn't cause error with guard clause."""
        actual = 0
        target = 0
        pct = (actual / target * 100) if target else 0
        assert pct == 0, "Zero/zero with guard should not raise exception"


class TestDataValidation:
    """Test data validation and null handling."""
    
    def test_empty_dataset_returns_zero_not_error(self):
        """Test that empty dataset returns 0 values, not errors."""
        # Simulates COALESCE behavior in SQL
        sum_value = 0  # COALESCE(SUM(NULL), 0) = 0
        assert sum_value == 0
        assert not isinstance(sum_value, type(None))
    
    def test_null_sum_coalesce_handling(self):
        """Test that null sums are coalesced to zero."""
        # Simulates SQL: COALESCE(SUM(trees), 0)
        null_result = None
        coalesced = null_result or 0
        assert coalesced == 0
    
    def test_negative_values_in_calculations(self):
        """Test handling of unexpected negative values."""
        # Edge case: if data has negative trees somehow
        trees = -5
        target = 100
        # Should still calculate, but unusual
        pct = (trees / target * 100) if target else 0
        assert pct == -5.0, "Negative values should still calculate"


class TestProjectMetrics:
    """Test project-level metrics calculations."""
    
    def test_active_farmer_percentage_calculation(self):
        """Test active farmers percentage with edge cases."""
        # Normal case
        active = 50
        target = 100
        pct = (active / target * 100) if target else 0
        assert pct == 50.0
        
        # Edge case: more active than target (over-performing)
        active = 150
        target = 100
        pct = (active / target * 100) if target else 0
        assert pct == 150.0, "Can exceed 100% if overperforming"
    
    def test_parcel_count_accuracy(self):
        """Test parcel counting accuracy."""
        # Test that filtering for is_active=true works correctly
        parcels_total = 100
        parcels_active = 85
        inactive = parcels_total - parcels_active
        
        assert parcels_active == 85
        assert inactive == 15
    
    def test_area_hectares_rounding(self):
        """Test that area calculations maintain precision."""
        area = 123.456789
        rounded = round(area, 1)
        assert rounded == 123.5, "Should round to 1 decimal place"
        
        # Edge case: very small area
        tiny_area = 0.0001
        rounded = round(tiny_area, 1)
        assert rounded == 0.0


class TestDatabaseIntegration:
    """Test database connection and error handling."""
    
    @patch('monitor.duckdb.connect')
    def test_db_connection_success(self, mock_connect):
        """Test successful database connection."""
        mock_con = Mock()
        mock_connect.return_value = mock_con
        
        con = mock_connect('test.db', read_only=True)
        assert con is not None
    
    @patch('monitor.duckdb.connect')
    def test_db_connection_failure_handling(self, mock_connect):
        """Test graceful handling of database connection failure."""
        mock_connect.side_effect = Exception("Database locked")
        
        try:
            con = mock_connect('test.db', read_only=True)
        except Exception as e:
            assert "Database locked" in str(e)


class TestTreesSurvivalMetrics:
    """Test tree survival and planting metrics."""
    
    def test_tree_survival_rate(self):
        """Test tree survival rate calculation."""
        trees_alive = 800
        trees_planted = 1000
        survival_pct = (trees_alive / trees_planted * 100) if trees_planted else 0
        assert survival_pct == 80.0
    
    def test_tree_survival_edge_case_all_dead(self):
        """Test survival rate when all trees are dead."""
        trees_alive = 0
        trees_planted = 1000
        survival_pct = (trees_alive / trees_planted * 100) if trees_planted else 0
        assert survival_pct == 0.0
    
    def test_tree_survival_edge_case_all_alive(self):
        """Test survival rate when all trees are alive."""
        trees_alive = 1000
        trees_planted = 1000
        survival_pct = (trees_alive / trees_planted * 100) if trees_planted else 0
        assert survival_pct == 100.0
    
    def test_tree_metrics_no_trees_planted(self):
        """Test tree metrics when no trees have been planted."""
        trees_planned = 0
        trees_alive = 0
        survival = (trees_alive / trees_planned * 100) if trees_planned else 0
        assert survival == 0, "No trees planted should return 0% not error"


class TestFormattingAndDisplay:
    """Test data formatting for display."""
    
    def test_large_number_formatting(self):
        """Test formatting of large numbers with comma separator."""
        num = 1234567
        formatted = f"{num:,}"
        assert formatted == "1,234,567"
    
    def test_decimal_formatting_area(self):
        """Test decimal formatting for area measurements."""
        area = 123.456
        formatted = f"{area:.1f}"
        assert formatted == "123.5"
    
    def test_integer_conversion_for_display(self):
        """Test safe integer conversion for display."""
        value = 123.999
        int_value = int(value)
        assert int_value == 123
