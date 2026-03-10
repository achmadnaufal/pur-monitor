# Changelog

All notable changes to the PUR Monitor project are documented in this file.

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
