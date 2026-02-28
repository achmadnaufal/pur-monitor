# PUR Latin America — Project Monitoring Toolkit

A lightweight CLI tool for monitoring PUR reforestation projects in Latin America,
powered by **DuckDB** and **Python 3.12**.

## Project Structure

```
pur-monitor/
├── setup.py        # Database setup + seed data
├── monitor.py      # CLI monitoring dashboard
├── queries.sql     # Reusable SQL views
├── pur_monitor.db  # DuckDB database (generated)
└── README.md
```

## Requirements

```bash
pip install duckdb rich
```

Python 3.12+ required.

## Quick Start

**1. Set up the database (first time only):**
```bash
cd pur-monitor
python3.12 setup.py
```
This creates `pur_monitor.db` with:
- 3 countries (Peru, Colombia, Brazil)
- 5 projects
- ~56 farmers
- 100 parcels
- 600 parcel visit records (6 months × 100 parcels)

**2. Run the monitoring dashboard:**

```bash
# KPI overview — total projects, farmers, parcels, trees vs. targets
python3.12 monitor.py summary

# Per-project progress table with % achievement
python3.12 monitor.py projects

# Top mortality causes ranked by tree loss
python3.12 monitor.py mortality

# Gender breakdown + active rate per project
python3.12 monitor.py farmers
```

## SQL Views

Load and query the views directly with DuckDB CLI:
```bash
duckdb pur_monitor.db < queries.sql
duckdb pur_monitor.db "SELECT * FROM v_latam_monitoring"
duckdb pur_monitor.db "SELECT * FROM v_mortality_analysis"
duckdb pur_monitor.db "SELECT * FROM v_farmer_demographics"
```

### View Reference

| View | Description |
|------|-------------|
| `v_latam_monitoring` | Per-project KPI rollup: farmers, parcels, trees alive, area, % vs. targets |
| `v_mortality_analysis` | Mortality cause ranking by trees lost + visit count |
| `v_farmer_demographics` | Gender breakdown, age stats, active rate per project |

## Schema Overview

```
regions → countries → projects → farmers → parcels → parcel_visits
                              ↘ project_targets
parcels → species / ref_erosion / ref_soil_texture / ref_mortality / ref_planting_model
parcel_visits → ref_mortality
```

## Sample Output

```
╭─────────────────────────────────────────────────╮
│ PUR Latin America — Monitoring Summary           │
╰─────────────────────────────────────────────────╯
┌──────────────────────┬──────────┬────────┬──────────────┐
│ KPI                  │   Actual │ Target │ % Achievement │
├──────────────────────┼──────────┼────────┼──────────────┤
│ Projects             │        5 │      5 │ —            │
│ Active Farmers       │       52 │    200 │ 26.0%        │
│ Active Parcels       │       95 │    410 │ 23.2%        │
│ Trees Alive (latest) │  107,324 │ 75,000 │ 143.1%       │
│ Area to Plant (ha)   │    437.5 │  605.0 │ 72.3%        │
└──────────────────────┴──────────┴────────┴──────────────┘
```

## Data Model Notes

- **parcel_visits**: Each visit records `trees_alive` and `trees_dead` for a specific
  parcel. The monitoring views use the **latest visit per parcel** to compute current
  tree survival.
- **project_targets**: One row per project with cumulative targets for the full project
  period.
- **mortality_id** on parcels: the "dominant" expected mortality risk; on visits: the
  observed cause that cycle.
- Kobo Toolbox submission IDs (`kobo_submission_id`) simulate real field data collection.
