# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.3.0] - 2026-03-05
### Added
- `cmd_export()`: export full project monitoring data to CSV or JSON with `python monitor.py export [json]`
- `cmd_species_breakdown()`: species distribution table across active parcels
- Both commands integrated into COMMANDS dict and usage help
### Improved
- README updated with new command reference table and export usage examples

## [1.2.0] - 2026-03-04
### Added
- Full DuckDB-backed monitoring CLI with 4 commands: summary, projects, mortality, farmers
- Rich terminal tables with color-coded % achievement
- Streamlit dashboard (app.py) with KPI cards and Plotly charts
- SQL views: v_latam_monitoring, v_mortality_analysis, v_farmer_demographics
- Seed data: 5 projects, 56 farmers, 100 parcels, 600 visit records across 3 countries

## [1.1.0] - 2026-03-02
### Added
- Initial CLI monitoring dashboard
- DuckDB schema setup
