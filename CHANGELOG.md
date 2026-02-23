# Changelog

All notable changes to the PUR Monitor project are documented in this file.

## [2.5.0] - 2026-03-25

### Added
- **Deforestation Pressure Index** (`deforestation_pressure_index.py`) — composite threat score for PUR project site prioritization
  - Five-driver weighted model: agricultural expansion (30%), road proximity (20%), population growth (15%), historical forest loss rate (25%), governance deficit (10%)
  - FAO/GFW-aligned normalization with historical loss rate scaled to 0–10
  - Five categorical pressure levels: Very Low → Critical
  - Dominant driver identification with percentage contribution to total score
  - Management recommendations and monitoring frequency per pressure level
  - Batch assessment with automatic DPI-ranked sorting
  - Portfolio summary with pressure distribution and high-risk site list
  - Configurable driver weights for regional calibration
- Unit tests: 20 new tests in `tests/test_deforestation_pressure_index.py`

## [2.4.0] - 2026-03-23

### Added
- `blue_carbon.py` — Blue Carbon Stock Calculator for coastal ecosystem projects
  - `BlueCarbonPlot` dataclass with full validation (ecosystem, zone, area, canopy)
  - `BlueCarbonCalculator` with IPCC Wetlands Supplement Tier 1 emission factors
  - `total_carbon_stock()` — biomass + soil stocks aggregated by ecosystem
  - `annual_sequestration()` — canopy-cover-weighted annual tCO2e/yr
  - `project_lifetime_credits()` — gross/net credit projection with discount rate
  - `ecosystem_summary()` — sorted per-ecosystem breakdown
  - Supports mangrove, seagrass, and tidal marsh ecosystems
  - Climate zones: equatorial, tropical, subtropical, temperate
- `data/sample_blue_carbon_plots.csv` — 10 realistic blue carbon plots from SE Asia
- 26 unit tests in `tests/test_blue_carbon.py`

### References
- IPCC Wetlands Supplement (2013)
- Verra VCS VM0033
- Howard et al. (2014) Coastal Blue Carbon

## [2.3.0] - 2026-03-15

### Added
- **Survival Trend Analysis** — `calculate_survival_trend()`: Compares tree survival rates across the N most-recent visits per parcel; classifies portfolio trend as improving/stable/declining with pp change
- **Top Mortality Parcels** — `get_top_mortality_parcels()`: Returns worst-performing parcels ranked by mortality rate with farmer name and visit date for targeted field follow-up
- **Unit Tests** — 8 new tests in `tests/test_survival_trend.py` (mocked DuckDB) for trend direction, validation errors, and missing data handling
- **README** — Added survival trend and mortality analysis usage examples

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
