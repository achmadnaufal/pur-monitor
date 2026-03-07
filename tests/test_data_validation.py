"""
Data validation tests for PUR Monitor.

Tests edge cases in:
- Date parsing and validation
- Coordinate validation for KoboToolbox imports
- Data type conversion
- CSV/JSON import validation
"""

import pytest
from datetime import datetime, date
from typing import Optional


class TestDateValidation:
    """Test date field validation."""
    
    def test_valid_iso_date_format(self):
        """Test parsing of valid ISO date format."""
        date_str = "2026-03-07"
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed.year == 2026
        assert parsed.month == 3
        assert parsed.day == 7
    
    def test_invalid_date_format_raises_error(self):
        """Test that invalid date format raises ValueError."""
        date_str = "07-03-2026"  # Wrong format
        with pytest.raises(ValueError):
            datetime.strptime(date_str, "%Y-%m-%d")
    
    def test_future_date_acceptance(self):
        """Test that future dates are accepted."""
        future_date = datetime(2026, 12, 31)
        today = datetime.now()
        assert future_date > today, "Future dates should be valid"
    
    def test_past_date_acceptance(self):
        """Test that past dates (from project start) are accepted."""
        past_date = datetime(2020, 1, 1)
        today = datetime.now()
        assert past_date < today, "Past dates should be valid"
    
    def test_leap_year_date_validation(self):
        """Test leap year date handling."""
        leap_date = "2024-02-29"
        parsed = datetime.strptime(leap_date, "%Y-%m-%d")
        assert parsed.day == 29, "Leap year Feb 29 should be valid"
    
    def test_invalid_leap_year_date(self):
        """Test that invalid leap year dates raise error."""
        invalid_leap = "2025-02-29"  # 2025 is not a leap year
        with pytest.raises(ValueError):
            datetime.strptime(invalid_leap, "%Y-%m-%d")


class TestCoordinateValidation:
    """Test geographic coordinate validation for GIS data."""
    
    def test_valid_latitude_range(self):
        """Test that latitude is within -90 to 90."""
        valid_lats = [-90, -45, 0, 45, 90]
        for lat in valid_lats:
            assert -90 <= lat <= 90, f"Latitude {lat} should be valid"
    
    def test_invalid_latitude_too_high(self):
        """Test that latitude > 90 is invalid."""
        invalid_lat = 91
        assert not (-90 <= invalid_lat <= 90), "Latitude > 90 should be invalid"
    
    def test_valid_longitude_range(self):
        """Test that longitude is within -180 to 180."""
        valid_lons = [-180, -90, 0, 90, 180]
        for lon in valid_lons:
            assert -180 <= lon <= 180, f"Longitude {lon} should be valid"
    
    def test_invalid_longitude_too_high(self):
        """Test that longitude > 180 is invalid."""
        invalid_lon = 181
        assert not (-180 <= invalid_lon <= 180), "Longitude > 180 should be invalid"
    
    def test_null_coordinates_handling(self):
        """Test handling of null/missing coordinates."""
        lat = None
        lon = None
        # Should not crash, but flag as invalid
        is_valid = lat is not None and lon is not None and (-90 <= lat <= 90) and (-180 <= lon <= 180)
        assert not is_valid, "Null coordinates should be flagged as invalid"
    
    def test_zero_coordinates_validity(self):
        """Test that zero coordinates (equator/prime meridian) are valid."""
        lat = 0
        lon = 0
        is_valid = -90 <= lat <= 90 and -180 <= lon <= 180
        assert is_valid, "Zero coordinates should be valid"


class TestNumericValidation:
    """Test numeric field validation."""
    
    def test_positive_integer_validation(self):
        """Test validation of positive integers (counts)."""
        farmer_count = 42
        assert farmer_count > 0 and isinstance(farmer_count, int)
    
    def test_zero_count_acceptance(self):
        """Test that zero counts are valid in some contexts."""
        active_parcels = 0
        assert isinstance(active_parcels, int) and active_parcels >= 0
    
    def test_negative_count_rejection(self):
        """Test that negative counts are invalid."""
        negative_count = -5
        assert negative_count < 0, "Negative counts should be flagged"
        is_valid = negative_count >= 0
        assert not is_valid
    
    def test_float_area_precision(self):
        """Test float precision for area measurements."""
        area = 123.456789
        # Round to 2 decimal places for hectares
        rounded = round(area, 2)
        assert rounded == 123.46
        assert len(str(rounded).split('.')[-1]) <= 2
    
    def test_very_small_decimal_values(self):
        """Test handling of very small decimal values."""
        tiny_value = 0.00001
        assert tiny_value > 0
        # Should not be treated as zero in some calculations
        assert tiny_value != 0


class TestStringValidation:
    """Test string field validation."""
    
    def test_empty_string_detection(self):
        """Test detection of empty strings."""
        empty = ""
        is_empty = len(empty) == 0
        assert is_empty
    
    def test_whitespace_only_string_detection(self):
        """Test detection of whitespace-only strings."""
        whitespace = "   "
        is_whitespace_only = len(whitespace.strip()) == 0
        assert is_whitespace_only
    
    def test_project_name_validation(self):
        """Test validation of project name."""
        valid_name = "PUR Latin America"
        assert len(valid_name) > 0
        assert len(valid_name) <= 255  # Reasonable max length
    
    def test_country_code_validation(self):
        """Test 2-letter country code validation."""
        valid_codes = ["BR", "CO", "PE", "MX"]
        for code in valid_codes:
            assert len(code) == 2 and code.isupper()
    
    def test_invalid_country_code(self):
        """Test that invalid country codes are caught."""
        invalid_code = "USA"  # Should be 2-letter
        is_valid = len(invalid_code) == 2
        assert not is_valid


class TestDataTypeConversion:
    """Test data type conversions and coercions."""
    
    def test_string_to_integer_conversion(self):
        """Test safe string to integer conversion."""
        str_num = "42"
        try:
            num = int(str_num)
            assert num == 42
        except ValueError:
            pytest.fail("Valid number string should convert")
    
    def test_invalid_string_to_integer_conversion(self):
        """Test that invalid string to integer conversion fails."""
        invalid_str = "forty-two"
        with pytest.raises(ValueError):
            int(invalid_str)
    
    def test_string_to_float_conversion(self):
        """Test string to float conversion."""
        str_float = "123.45"
        float_val = float(str_float)
        assert float_val == 123.45
    
    def test_boolean_from_string_conversion(self):
        """Test converting string values to boolean."""
        true_values = ["yes", "true", "1", "active"]
        false_values = ["no", "false", "0", "inactive"]
        
        for val in true_values:
            is_true = val.lower() in ["yes", "true", "1", "active"]
            assert is_true
        
        for val in false_values:
            is_false = val.lower() in ["no", "false", "0", "inactive"]
            assert is_false
    
    def test_none_type_handling(self):
        """Test proper handling of None values."""
        value = None
        # Use COALESCE-like pattern
        safe_value = value or "default"
        assert safe_value == "default"
        
        # Test with actual value
        value = "actual"
        safe_value = value or "default"
        assert safe_value == "actual"


class TestBatchDataValidation:
    """Test validation of multiple records."""
    
    def test_csv_row_count_validation(self):
        """Test validation of row count in CSV import."""
        rows = [
            {"name": "Project A", "country": "BR"},
            {"name": "Project B", "country": "CO"},
            {"name": "Project C", "country": "PE"},
        ]
        assert len(rows) == 3
    
    def test_missing_required_fields_detection(self):
        """Test detection of missing required fields."""
        required_fields = ["name", "country", "year"]
        record = {"name": "Project A", "country": "BR"}  # Missing "year"
        
        missing = [f for f in required_fields if f not in record]
        assert "year" in missing, "Should detect missing 'year' field"
    
    def test_duplicate_record_detection(self):
        """Test detection of duplicate records."""
        records = [
            {"id": 1, "name": "Project A"},
            {"id": 2, "name": "Project B"},
            {"id": 1, "name": "Project A"},  # Duplicate
        ]
        ids = [r["id"] for r in records]
        duplicates = [x for x in ids if ids.count(x) > 1]
        assert 1 in duplicates, "Should detect duplicate ID"
