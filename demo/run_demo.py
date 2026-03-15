#!/usr/bin/env python3
"""
PUR Monitor — CLI Demo
Reads live DuckDB database and prints key KPIs without requiring Rich.
Run from the pur-monitor directory: python3 demo/run_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import duckdb

DB_PATH = Path(__file__).parent.parent / "pur_monitor.db"


def main():
    print("=" * 62)
    print("  PUR Monitor — KPI Demo")
    print("  NbS Field Project Monitoring (Latin America)")
    print("=" * 62)
    print()

    con = duckdb.connect(str(DB_PATH), read_only=True)

    # ── Portfolio KPIs ──────────────────────────────────────────
    kpis = con.execute("""
        SELECT
            COUNT(DISTINCT p.id)                AS project_count,
            COUNT(DISTINCT f.id)                AS total_farmers,
            SUM(CASE WHEN f.is_active THEN 1 ELSE 0 END) AS active_farmers,
            COUNT(DISTINCT pr.id)               AS active_parcels,
            COALESCE(SUM(pr.number_of_tree), 0) AS trees_planned
        FROM projects p
        LEFT JOIN farmers f ON f.project_id = p.id
        LEFT JOIN parcels pr ON pr.farmer_id = f.id
    """).fetchone()

    alive = con.execute("""
        SELECT SUM(pv.trees_alive)
        FROM parcel_visits pv
        INNER JOIN (
            SELECT parcel_id, MAX(visit_date) AS last_visit
            FROM parcel_visits GROUP BY parcel_id
        ) lv ON pv.parcel_id = lv.parcel_id AND pv.visit_date = lv.last_visit
    """).fetchone()[0]

    targets = con.execute("""
        SELECT SUM(target_trees), SUM(target_farmers), SUM(target_parcels)
        FROM project_targets
    """).fetchone()

    trees_planned = kpis[4]
    survival_rate = (alive / trees_planned * 100) if trees_planned else 0
    farmer_ach = (kpis[2] / targets[1] * 100) if targets[1] else 0

    print("Portfolio KPI Summary:")
    print(f"  Projects active       : {kpis[0]}")
    print(f"  Active farmers        : {kpis[2]}/{targets[1]} ({farmer_ach:.1f}% of target)")
    print(f"  Active parcels        : {kpis[3]}/{targets[2]}")
    print(f"  Trees planned         : {trees_planned:,}")
    print(f"  Trees alive (latest)  : {alive:,}")
    print(f"  Survival rate         : {survival_rate:.1f}%")
    print()

    # ── Per-Project Breakdown ───────────────────────────────────
    projects = con.execute("""
        SELECT p.project_name, p.project_country,
               COUNT(DISTINCT f.id)                AS farmers,
               COALESCE(SUM(pr.number_of_tree), 0) AS trees
        FROM projects p
        LEFT JOIN farmers f ON f.project_id = p.id
        LEFT JOIN parcels pr ON pr.farmer_id = f.id
        GROUP BY p.id, p.project_name, p.project_country
        ORDER BY p.id
    """).fetchall()

    print("Per-Project Breakdown:")
    print(f"  {'Country':<10} {'Project':<38} {'Farmers':>7} {'Trees':>9}")
    print("  " + "-" * 68)
    for r in projects:
        print(f"  {r[1]:<10} {r[0]:<38} {r[2]:>7} {r[3]:>9,}")
    print()

    # ── Top Mortality Causes ────────────────────────────────────
    mort = con.execute("""
        SELECT rm.mortality_name, COUNT(*) AS incidents, SUM(pv.trees_dead) AS tree_loss
        FROM parcel_visits pv
        JOIN ref_mortality rm ON pv.mortality_id = rm.id
        GROUP BY rm.mortality_name
        ORDER BY tree_loss DESC
        LIMIT 5
    """).fetchall()

    print("Top Mortality Causes:")
    print(f"  {'Cause':<28} {'Incidents':>9} {'Tree Loss':>10}")
    print("  " + "-" * 50)
    for m in mort:
        print(f"  {m[0]:<28} {m[1]:>9} {m[2]:>10,}")
    print()

    # ── Farmer Demographics ─────────────────────────────────────
    gender = con.execute("""
        SELECT gender, COUNT(*) AS n,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM farmers GROUP BY gender
    """).fetchall()

    active_stat = con.execute("""
        SELECT SUM(CASE WHEN is_active THEN 1 ELSE 0 END), COUNT(*),
               ROUND(100.0 * SUM(CASE WHEN is_active THEN 1 ELSE 0 END) / COUNT(*), 1)
        FROM farmers
    """).fetchone()

    print("Farmer Demographics:")
    for g in gender:
        print(f"  {g[0]}: {g[1]} ({g[2]}%)")
    print(f"  Active rate: {active_stat[0]}/{active_stat[1]} ({active_stat[2]}%)")
    print()

    con.close()
    print("=" * 62)
    print("  ✅ Demo complete — Launch Streamlit app:")
    print("     streamlit run app.py")
    print("=" * 62)


if __name__ == "__main__":
    main()
