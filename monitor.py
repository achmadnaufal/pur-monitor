#!/usr/bin/env python3.12
"""
monitor.py — PUR Latin America Project Monitoring CLI
Usage:
    python monitor.py summary    # KPI overview
    python monitor.py projects   # Per-project progress
    python monitor.py mortality  # Top mortality causes
    python monitor.py farmers    # Gender breakdown + active rate
"""

import sys
import duckdb
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

DB_PATH = "pur_monitor.db"
console = Console()


def get_con():
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        console.print(f"[red]Cannot open {DB_PATH}: {e}[/red]")
        console.print("[yellow]Run: python setup.py[/yellow]")
        sys.exit(1)


def cmd_summary():
    con = get_con()

    # KPI queries
    totals = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM projects)                          AS total_projects,
            (SELECT COUNT(*) FROM farmers WHERE is_active)           AS active_farmers,
            (SELECT COUNT(*) FROM parcels  WHERE is_active)          AS active_parcels,
            (SELECT COALESCE(SUM(number_of_tree),0) FROM parcels WHERE is_active) AS total_trees_planned,
            (SELECT COALESCE(SUM(area_to_plant),0) FROM parcels WHERE is_active)  AS total_area_ha
    """).fetchone()

    # Latest visit alive trees
    latest_alive = con.execute("""
        SELECT COALESCE(SUM(v.trees_alive), 0)
        FROM parcel_visits v
        INNER JOIN (
            SELECT parcel_id, MAX(visit_date) AS last_date
            FROM parcel_visits GROUP BY parcel_id
        ) latest ON v.parcel_id = latest.parcel_id AND v.visit_date = latest.last_date
    """).fetchone()[0]

    # Targets
    tgt = con.execute("""
        SELECT
            SUM(target_trees)         AS tgt_trees,
            SUM(target_area_hectares) AS tgt_area,
            SUM(target_farmers)       AS tgt_farmers,
            SUM(target_parcels)       AS tgt_parcels
        FROM project_targets
    """).fetchone()

    total_projects, active_farmers, active_parcels, total_trees, total_area = totals
    tgt_trees, tgt_area, tgt_farmers, tgt_parcels = tgt

    pct_trees   = latest_alive / tgt_trees * 100   if tgt_trees   else 0
    pct_area    = total_area   / tgt_area   * 100   if tgt_area    else 0
    pct_farmers = active_farmers / tgt_farmers * 100 if tgt_farmers else 0
    pct_parcels = active_parcels / tgt_parcels * 100 if tgt_parcels else 0

    console.print(Panel("[bold green]PUR Latin America — Monitoring Summary[/bold green]",
                        expand=False))

    t = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("KPI", style="bold")
    t.add_column("Actual", justify="right")
    t.add_column("Target", justify="right")
    t.add_column("% Achievement", justify="right")

    def pct_color(p):
        if p >= 80: return f"[green]{p:.1f}%[/green]"
        if p >= 50: return f"[yellow]{p:.1f}%[/yellow]"
        return f"[red]{p:.1f}%[/red]"

    t.add_row("Projects",          str(total_projects),        "5",               "—")
    t.add_row("Active Farmers",    str(active_farmers),        str(int(tgt_farmers)),  pct_color(pct_farmers))
    t.add_row("Active Parcels",    str(active_parcels),        str(int(tgt_parcels)),  pct_color(pct_parcels))
    t.add_row("Trees Planted",     f"{total_trees:,}",         f"{int(tgt_trees):,}",  "—")
    t.add_row("Trees Alive (latest)", f"{int(latest_alive):,}", f"{int(tgt_trees):,}", pct_color(pct_trees))
    t.add_row("Area to Plant (ha)", f"{total_area:.1f}",       f"{tgt_area:.1f}",      pct_color(pct_area))

    console.print(t)
    con.close()


def cmd_projects():
    con = get_con()

    rows = con.execute("""
        WITH latest_visits AS (
            SELECT v.project_id,
                   SUM(v.trees_alive) AS alive_trees
            FROM parcel_visits v
            INNER JOIN (
                SELECT parcel_id, MAX(visit_date) AS last_date
                FROM parcel_visits GROUP BY parcel_id
            ) lv ON v.parcel_id = lv.parcel_id AND v.visit_date = lv.last_date
            GROUP BY v.project_id
        ),
        parcel_stats AS (
            SELECT project_id,
                   COUNT(*) FILTER (WHERE is_active) AS active_parcels,
                   SUM(area_to_plant) FILTER (WHERE is_active) AS area_planted,
                   SUM(number_of_tree) FILTER (WHERE is_active) AS trees_planned
            FROM parcels GROUP BY project_id
        ),
        farmer_stats AS (
            SELECT project_id, COUNT(*) FILTER (WHERE is_active) AS active_farmers
            FROM farmers GROUP BY project_id
        )
        SELECT
            p.id,
            p.project_name,
            p.project_country,
            p.project_year,
            COALESCE(fs.active_farmers, 0)     AS farmers,
            pt.target_farmers,
            COALESCE(ps.active_parcels, 0)     AS parcels,
            pt.target_parcels,
            COALESCE(lv.alive_trees, 0)        AS trees_alive,
            pt.target_trees,
            ROUND(COALESCE(ps.area_planted,0),1)   AS area_ha,
            pt.target_area_hectares
        FROM projects p
        LEFT JOIN project_targets pt ON pt.project_id = p.id
        LEFT JOIN parcel_stats ps    ON ps.project_id = p.id
        LEFT JOIN farmer_stats fs    ON fs.project_id = p.id
        LEFT JOIN latest_visits lv   ON lv.project_id = p.id
        ORDER BY p.id
    """).fetchall()

    console.print(Panel("[bold green]PUR Latin America — Project Progress[/bold green]",
                        expand=False))

    t = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("ID",      justify="right")
    t.add_column("Project", style="bold")
    t.add_column("Country")
    t.add_column("Year",    justify="right")
    t.add_column("Farmers\nActual/Tgt", justify="right")
    t.add_column("Parcels\nActual/Tgt", justify="right")
    t.add_column("Trees Alive\nActual/Tgt", justify="right")
    t.add_column("Area (ha)\nActual/Tgt",  justify="right")
    t.add_column("Tree %", justify="right")

    for row in rows:
        (pid, pname, country, year, farmers, tgt_f, parcels, tgt_p,
         trees_alive, tgt_trees, area, tgt_area) = row
        pct = trees_alive / tgt_trees * 100 if tgt_trees else 0
        pct_txt = f"[green]{pct:.0f}%[/green]" if pct >= 80 \
                  else (f"[yellow]{pct:.0f}%[/yellow]" if pct >= 50 else f"[red]{pct:.0f}%[/red]")
        t.add_row(
            str(pid), pname, country, str(year),
            f"{farmers}/{tgt_f}",
            f"{parcels}/{tgt_p}",
            f"{trees_alive:,}/{tgt_trees:,}",
            f"{area}/{tgt_area}",
            pct_txt,
        )

    console.print(t)
    con.close()


def cmd_mortality():
    con = get_con()

    rows = con.execute("""
        SELECT
            rm.mortality_name,
            COUNT(*) AS visit_count,
            SUM(pv.trees_dead) AS total_dead_trees,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_visits
        FROM parcel_visits pv
        JOIN ref_mortality rm ON rm.id = pv.mortality_id
        WHERE pv.trees_dead > 0
        GROUP BY rm.mortality_name
        ORDER BY total_dead_trees DESC
    """).fetchall()

    console.print(Panel("[bold green]PUR Latin America — Mortality Analysis[/bold green]",
                        expand=False))

    t = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("Rank",          justify="right")
    t.add_column("Mortality Cause", style="bold")
    t.add_column("Visits w/ Loss", justify="right")
    t.add_column("Total Trees Dead", justify="right")
    t.add_column("% of Visits", justify="right")

    total_dead = sum(r[2] for r in rows)
    for i, (cause, visits, dead, pct_v) in enumerate(rows, 1):
        bar_pct = dead / total_dead * 100 if total_dead else 0
        bar = "█" * int(bar_pct / 5)
        color = "red" if i <= 2 else ("yellow" if i <= 4 else "green")
        t.add_row(
            str(i),
            cause,
            str(visits),
            f"[{color}]{dead:,}[/{color}]",
            f"{pct_v:.1f}%  {bar}",
        )

    console.print(t)
    console.print(f"\n[dim]Total trees lost across all visits: {total_dead:,}[/dim]")
    con.close()


def cmd_farmers():
    con = get_con()

    rows = con.execute("""
        SELECT
            p.project_name,
            p.project_country,
            COUNT(*) AS total_farmers,
            COUNT(*) FILTER (WHERE f.gender = 'F') AS female,
            COUNT(*) FILTER (WHERE f.gender = 'M') AS male,
            COUNT(*) FILTER (WHERE f.is_active)    AS active,
            ROUND(100.0 * COUNT(*) FILTER (WHERE f.gender = 'F') / COUNT(*), 1) AS pct_female,
            ROUND(100.0 * COUNT(*) FILTER (WHERE f.is_active)    / COUNT(*), 1) AS pct_active,
            ROUND(AVG(f.age), 1) AS avg_age
        FROM farmers f
        JOIN projects p ON p.id = f.project_id
        GROUP BY p.id, p.project_name, p.project_country
        ORDER BY p.id
    """).fetchall()

    # Totals
    totals = con.execute("""
        SELECT
            COUNT(*), 
            COUNT(*) FILTER (WHERE gender='F'),
            COUNT(*) FILTER (WHERE gender='M'),
            COUNT(*) FILTER (WHERE is_active),
            ROUND(100.0 * COUNT(*) FILTER (WHERE gender='F') / COUNT(*), 1),
            ROUND(100.0 * COUNT(*) FILTER (WHERE is_active)  / COUNT(*), 1),
            ROUND(AVG(age), 1)
        FROM farmers
    """).fetchone()

    console.print(Panel("[bold green]PUR Latin America — Farmer Demographics[/bold green]",
                        expand=False))

    t = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    t.add_column("Project",      style="bold")
    t.add_column("Country")
    t.add_column("Total", justify="right")
    t.add_column("Female", justify="right")
    t.add_column("Male",   justify="right")
    t.add_column("% Female", justify="right")
    t.add_column("Active", justify="right")
    t.add_column("% Active", justify="right")
    t.add_column("Avg Age", justify="right")

    def female_color(p):
        if p >= 40: return f"[green]{p}%[/green]"
        if p >= 25: return f"[yellow]{p}%[/yellow]"
        return f"[red]{p}%[/red]"

    for (pname, country, total, female, male, active, pct_f, pct_a, avg_age) in rows:
        t.add_row(pname, country, str(total), str(female), str(male),
                  female_color(pct_f), str(active), f"{pct_a}%", str(avg_age))

    t.add_section()
    tot_total, tot_f, tot_m, tot_a, tot_pct_f, tot_pct_a, tot_avg = totals
    t.add_row("[bold]TOTAL / AVG[/bold]", "All", str(tot_total), str(tot_f), str(tot_m),
              female_color(tot_pct_f), str(tot_a), f"{tot_pct_a}%", str(tot_avg))

    console.print(t)
    con.close()


COMMANDS = {
    "summary":   (cmd_summary,   "KPI overview across all projects"),
    "projects":  (cmd_projects,  "Per-project progress vs. targets"),
    "mortality": (cmd_mortality, "Top mortality causes ranked by tree loss"),
    "farmers":   (cmd_farmers,   "Gender breakdown + active rate per project"),
}


def usage():
    console.print("\n[bold]PUR Monitor[/bold] — Latin America Reforestation Tracker\n")
    console.print("[bold]Usage:[/bold]  python monitor.py <command>\n")
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("cmd", style="bold green")
    t.add_column("desc")
    for cmd, (_, desc) in COMMANDS.items():
        t.add_row(f"  {cmd}", desc)
    console.print(t)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        usage()
        sys.exit(0 if len(sys.argv) < 2 else 1)

    fn, _ = COMMANDS[sys.argv[1]]
    fn()
