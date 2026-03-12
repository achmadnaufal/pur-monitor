# Changelog

All notable changes to the PUR Monitor project are documented in this file.

## [2.2.0] - 2026-03-12

### Added

- **Carbon Sequestration Analytics**: New `calculate_carbon_sequestration()` method in PURAnalytics
  - Default 15 kg CO2/tree/year rate (conservative NbS average)
  - Support for custom species-specific carbon rates
  - 10-year and 30-year projection calculations
  - Edge case handling for empty datasets
- **Comprehensive Test Suite for Carbon Analytics**: 
  - 5 new unit tests in `test_carbon_sequestration.py`
  - Edge case validation (invalid carbon rates, boundary conditions)
  - Consistency checks for projections
- **Enhanced Module Documentation**:
  - Module-level docstrings with usage examples
  - Improved function docstrings across all methods
  - Edge case handling documentation
  - Type hints and error documentation
- **Carbon Sequestration Examples in README**:
  - Example code for default and custom carbon rate calculations
  - Typical sequestration rates by species/land use type
  - Integration examples for stakeholder reporting

### Improved

- All analytics methods now include comprehensive docstrings with return types, edge cases, and error conditions
- Better error handling in `get_tree_survival_stats()` and `get_farmer_engagement_metrics()` (NULLIF guards)
- Added input validation to `__init__()` and `calculate_planting_completion_rate()`
- Improved database connection management with try/finally blocks

### Fixed

- Division-by-zero protection in survival rate calculations
- Boundary condition handling in planting completion rate (days_back validation)
- Empty farmer table handling in engagement metrics calculation

## [2.1.0] - 2026-03-10

### Added

- **Advanced Analytics Module**: New `analytics.py` with PURAnalytics class
  - `get_tree_survival_stats()`: Calculate survival rates across parcels
  - `get_farmer_engagement_metrics()`: Track farmer engagement and gender distribution
  - `get_project_status_summary()`: Project-level KPI summary
  - `calculate_planting_completion_rate()`: Track planting progress
- **Comprehensive Test Suite**: 
  - 16 new tests for database operations
  - Tests for schema integrity, data insertion, analytics queries
  - Tests for tree planting metrics and survival rates
- **Enhanced Documentation**: Detailed docstrings for all new methods

### Changed

- Improved database query performance in analytics functions
- Enhanced error handling in database connections
- Standardized metric naming conventions

### Fixed

- Proper handling of NULL values in aggregate queries
- Corrected survival rate calculations

## [2.0.0] - 2026-02-01

### Added

- DuckDB integration for efficient data management
- CLI monitoring interface
- KPI summary dashboard
- Per-project progress tracking

## [1.0.0] - 2025-12-01

### Added

- Initial PUR monitoring system
