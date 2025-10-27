#!/usr/bin/env python3.12
"""
app.py — PUR Latin America Monitoring Dashboard
Streamlit + Plotly + DuckDB
"""

import os
import duckdb
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "pur_monitor.db"

st.set_page_config(
    page_title="PUR LatAm Monitor",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .kpi-card {
    background: #1a1f2e;
    border: 1px solid #2d3447;
    border-radius: 10px;
    padding: 20px 16px;
    text-align: center;
  }
  .kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #4CAF50;
    margin: 0;
  }
  .kpi-label {
    font-size: 0.78rem;
    color: #9aa3b5;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .section-header {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e0e0e0;
    border-left: 3px solid #4CAF50;
    padding-left: 10px;
    margin: 24px 0 12px 0;
  }
  .flag-box {
    background: #2a1f1f;
    border: 1px solid #7f3030;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 0.9rem;
  }
  div[data-testid="stDataFrame"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── DB helpers ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return duckdb.connect(str(DB_PATH), read_only=True)

def q(sql: str, params=None) -> pd.DataFrame:
    con = get_conn()
    if params:
        return con.execute(sql, params).df()
    return con.execute(sql).df()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌱 PUR LatAm Monitor")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Overview", "📁 Projects", "💀 Mortality", "👩‍🌾 Farmers", "🔍 Data Quality"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### Filters")

    all_countries = q("SELECT DISTINCT project_country FROM projects ORDER BY 1")["project_country"].tolist()
    all_years     = q("SELECT DISTINCT project_year    FROM projects ORDER BY 1")["project_year"].tolist()

    sel_countries = st.multiselect("Country", all_countries, default=all_countries)
    sel_years     = st.multiselect("Year",    all_years,    default=all_years)
    active_only   = st.toggle("Active farmers/parcels only", value=False)

    if not sel_countries:
        sel_countries = all_countries
    if not sel_years:
        sel_years = all_years

    countries_str = ", ".join(f"'{c}'" for c in sel_countries)
    years_str     = ", ".join(str(y) for y in sel_years)
    active_farmer = "AND f.is_active = TRUE" if active_only else ""
    active_parcel = "AND p.is_active = TRUE" if active_only else ""

    st.markdown("---")
    st.caption("Data: PUR Projet — Latin America")

# ─── Shared filter clause for projects ────────────────────────────────────────
proj_where = f"WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})"

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.markdown("# 📊 Overview")
    st.markdown(f"*Showing: {', '.join(sel_countries)} · {', '.join(str(y) for y in sel_years)}*")

    # ── KPIs ─────────────────────────────────────────────────────────────────
    kpi_sql = f"""
    SELECT
        COUNT(DISTINCT pr.id)                                          AS total_projects,
        COUNT(DISTINCT CASE WHEN f.is_active THEN f.id END)           AS active_farmers,
        COUNT(DISTINCT CASE WHEN p.is_active THEN p.id END)           AS active_parcels,
        COALESCE(SUM(CASE WHEN pv.rn = 1 THEN pv.trees_alive END), 0) AS trees_alive,
        COALESCE(SUM(p.area_to_plant), 0)                             AS area_planted,
        COALESCE(SUM(pt.target_area_hectares), 0)                     AS area_target
    FROM projects pr
    LEFT JOIN farmers f  ON f.project_id  = pr.id
    LEFT JOIN parcels p  ON p.project_id  = pr.id
    LEFT JOIN project_targets pt ON pt.project_id = pr.id
    LEFT JOIN (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY parcel_id ORDER BY visit_date DESC) AS rn
        FROM parcel_visits
    ) pv ON pv.parcel_id = p.id
    {proj_where}
    """
    kpi = q(kpi_sql).iloc[0]
    area_pct = (kpi["area_planted"] / kpi["area_target"] * 100) if kpi["area_target"] > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    def kpi_card(col, value, label):
        col.markdown(f"""
        <div class="kpi-card">
          <p class="kpi-value">{value}</p>
          <p class="kpi-label">{label}</p>
        </div>""", unsafe_allow_html=True)

    kpi_card(c1, int(kpi["total_projects"]),  "Total Projects")
    kpi_card(c2, f"{int(kpi['active_farmers']):,}", "Active Farmers")
    kpi_card(c3, f"{int(kpi['active_parcels']):,}", "Active Parcels")
    kpi_card(c4, f"{int(kpi['trees_alive']):,}",    "Trees Alive")
    kpi_card(c5, f"{area_pct:.1f}%",                "Area Achievement")

    st.markdown("")

    col_l, col_r = st.columns(2)

    # ── Bar: Trees alive by country ──────────────────────────────────────────
    with col_l:
        st.markdown('<div class="section-header">Trees Alive by Country</div>', unsafe_allow_html=True)
        bar_sql = f"""
        SELECT pr.project_country AS country,
               SUM(pv.trees_alive) AS trees_alive
        FROM parcel_visits pv
        JOIN parcels p  ON p.id  = pv.parcel_id
        JOIN projects pr ON pr.id = p.project_id
        WHERE pv.visit_date = (
            SELECT MAX(v2.visit_date) FROM parcel_visits v2 WHERE v2.parcel_id = pv.parcel_id
        )
        AND pr.project_country IN ({countries_str})
        AND pr.project_year    IN ({years_str})
        GROUP BY pr.project_country
        ORDER BY trees_alive DESC
        """
        df_bar = q(bar_sql)
        if not df_bar.empty:
            fig = px.bar(
                df_bar, x="country", y="trees_alive",
                color="country",
                color_discrete_sequence=["#4CAF50","#2196F3","#FF9800"],
                labels={"trees_alive": "Trees Alive", "country": "Country"},
                template="plotly_dark",
            )
            fig.update_layout(
                plot_bgcolor="#1a1f2e", paper_bgcolor="#1a1f2e",
                showlegend=False, margin=dict(t=20, b=10),
                xaxis=dict(gridcolor="#2d3447"),
                yaxis=dict(gridcolor="#2d3447"),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Line: Monthly tree survival trend ────────────────────────────────────
    with col_r:
        st.markdown('<div class="section-header">Monthly Tree Survival Trend</div>', unsafe_allow_html=True)
        trend_sql = f"""
        SELECT DATE_TRUNC('month', pv.visit_date) AS month,
               SUM(pv.trees_alive)                AS trees_alive
        FROM parcel_visits pv
        JOIN projects pr ON pr.id = pv.project_id
        WHERE pr.project_country IN ({countries_str})
        AND   pr.project_year    IN ({years_str})
        GROUP BY 1
        ORDER BY 1
        """
        df_trend = q(trend_sql)
        if not df_trend.empty:
            fig2 = px.line(
                df_trend, x="month", y="trees_alive",
                markers=True,
                labels={"trees_alive": "Trees Alive", "month": "Month"},
                template="plotly_dark",
                color_discrete_sequence=["#4CAF50"],
            )
            fig2.update_traces(line=dict(width=2.5))
            fig2.update_layout(
                plot_bgcolor="#1a1f2e", paper_bgcolor="#1a1f2e",
                margin=dict(t=20, b=10),
                xaxis=dict(gridcolor="#2d3447"),
                yaxis=dict(gridcolor="#2d3447"),
            )
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PROJECTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Projects":
    st.markdown("# 📁 Projects")

    proj_sql = f"""
    SELECT
        pr.id,
        pr.project_name,
        pr.project_country                                              AS country,
        pr.project_year                                                 AS year,
        COUNT(DISTINCT f.id)                                            AS farmers,
        COUNT(DISTINCT p.id)                                            AS parcels,
        COALESCE(SUM(CASE WHEN pv.rn = 1 THEN pv.trees_alive END), 0)  AS trees_alive,
        COALESCE(SUM(p.area_to_plant), 0)                               AS area_planted_ha,
        COALESCE(MAX(pt.target_area_hectares), 0)                       AS target_area_ha,
        COALESCE(MAX(pt.target_trees), 0)                               AS target_trees
    FROM projects pr
    LEFT JOIN farmers f  ON f.project_id  = pr.id
    LEFT JOIN parcels p  ON p.project_id  = pr.id
    LEFT JOIN project_targets pt ON pt.project_id = pr.id
    LEFT JOIN (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY parcel_id ORDER BY visit_date DESC) AS rn
        FROM parcel_visits
    ) pv ON pv.parcel_id = p.id
    {proj_where}
    GROUP BY pr.id, pr.project_name, pr.project_country, pr.project_year
    ORDER BY pr.project_year, pr.project_country
    """
    df_proj = q(proj_sql)
    df_proj["area_pct"] = df_proj.apply(
        lambda r: (r["area_planted_ha"] / r["target_area_ha"] * 100) if r["target_area_ha"] > 0 else 0, axis=1
    )
    df_proj["tree_pct"] = df_proj.apply(
        lambda r: (r["trees_alive"] / r["target_trees"] * 100) if r["target_trees"] > 0 else 0, axis=1
    )

    # Table
    st.markdown('<div class="section-header">Project Summary Table</div>', unsafe_allow_html=True)
    display = df_proj[[
        "project_name","country","year","farmers","parcels",
        "trees_alive","area_planted_ha","target_area_ha","area_pct"
    ]].copy()
    display.columns = [
        "Project","Country","Year","Farmers","Parcels",
        "Trees Alive","Area Planted (ha)","Target Area (ha)","Area %"
    ]
    display["Area Planted (ha)"] = display["Area Planted (ha)"].round(1)
    display["Target Area (ha)"]  = display["Target Area (ha)"].round(1)
    display["Area %"]            = display["Area %"].round(1)
    st.dataframe(display, use_container_width=True, hide_index=True)

    # Progress bars
    st.markdown('<div class="section-header">Tree Achievement by Project</div>', unsafe_allow_html=True)
    for _, row in df_proj.iterrows():
        pct = min(row["tree_pct"], 150)  # cap display at 150%
        raw_pct = row["tree_pct"]
        if raw_pct >= 100:
            color = "#4CAF50"
            badge = "🟢"
        elif raw_pct >= 75:
            color = "#FFC107"
            badge = "🟡"
        else:
            color = "#f44336"
            badge = "🔴"

        st.markdown(f"""
        <div style="margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="font-size:0.9rem;">{badge} <b>{row['project_name']}</b> ({row['country']}, {row['year']})</span>
            <span style="font-size:0.9rem; color:{color}; font-weight:600;">{raw_pct:.1f}%</span>
          </div>
          <div style="background:#2d3447; border-radius:6px; height:12px; overflow:hidden;">
            <div style="width:{min(pct,100):.1f}%; background:{color}; height:100%; border-radius:6px; transition:width 0.4s;"></div>
          </div>
          <div style="font-size:0.75rem; color:#9aa3b5; margin-top:2px;">
            {int(row['trees_alive']):,} alive of {int(row['target_trees']):,} target trees
          </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MORTALITY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💀 Mortality":
    st.markdown("# 💀 Mortality Analysis")

    mort_sql = f"""
    SELECT
        rm.mortality_name                AS cause,
        SUM(pv.trees_dead)               AS trees_dead,
        COUNT(DISTINCT pv.parcel_id)     AS parcels_affected
    FROM parcel_visits pv
    JOIN ref_mortality rm ON rm.id = pv.mortality_id
    JOIN projects pr      ON pr.id = pv.project_id
    WHERE pr.project_country IN ({countries_str})
    AND   pr.project_year    IN ({years_str})
    GROUP BY rm.mortality_name
    ORDER BY trees_dead DESC
    """
    df_mort = q(mort_sql)

    worst_proj_sql = f"""
    SELECT pr.project_name, SUM(pv.trees_dead) AS trees_dead
    FROM parcel_visits pv
    JOIN projects pr ON pr.id = pv.project_id
    WHERE pr.project_country IN ({countries_str})
    AND   pr.project_year    IN ({years_str})
    GROUP BY pr.project_name
    ORDER BY trees_dead DESC
    LIMIT 1
    """
    df_worst = q(worst_proj_sql)

    # Summary stats
    col1, col2, col3 = st.columns(3)
    total_lost  = int(df_mort["trees_dead"].sum()) if not df_mort.empty else 0
    worst_cause = df_mort.iloc[0]["cause"] if not df_mort.empty else "N/A"
    worst_proj  = df_worst.iloc[0]["project_name"] if not df_worst.empty else "N/A"

    def stat_card(col, val, label, icon="📌"):
        col.markdown(f"""
        <div class="kpi-card">
          <p class="kpi-value" style="font-size:1.6rem;">{val}</p>
          <p class="kpi-label">{icon} {label}</p>
        </div>""", unsafe_allow_html=True)

    stat_card(col1, f"{total_lost:,}", "Total Trees Lost", "🌲")
    stat_card(col2, worst_cause,        "Worst Cause",      "⚠️")
    stat_card(col3, worst_proj,         "Most Affected Project", "📍")

    st.markdown("")
    st.markdown('<div class="section-header">Mortality Causes — Trees Dead (Ranked)</div>', unsafe_allow_html=True)

    if not df_mort.empty:
        fig = px.bar(
            df_mort.sort_values("trees_dead"), x="trees_dead", y="cause",
            orientation="h",
            color="trees_dead",
            color_continuous_scale=["#4CAF50","#FFC107","#f44336"],
            labels={"trees_dead": "Trees Dead", "cause": "Cause"},
            template="plotly_dark",
            text="trees_dead",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            plot_bgcolor="#1a1f2e", paper_bgcolor="#1a1f2e",
            margin=dict(t=20, b=10, l=160),
            xaxis=dict(gridcolor="#2d3447"),
            yaxis=dict(gridcolor="#2d3447"),
            coloraxis_showscale=False,
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: FARMERS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👩‍🌾 Farmers":
    st.markdown("# 👩‍🌾 Farmers")

    gender_sql = f"""
    SELECT
        CASE WHEN f.gender = 'F' THEN 'Female' ELSE 'Male' END AS gender,
        COUNT(*) AS count
    FROM farmers f
    JOIN projects pr ON pr.id = f.project_id
    WHERE pr.project_country IN ({countries_str})
    AND   pr.project_year    IN ({years_str})
    {active_farmer.replace('f.', 'f.')}
    GROUP BY f.gender
    """
    df_gender = q(gender_sql)

    farmer_stats_sql = f"""
    SELECT
        pr.project_name,
        pr.project_country AS country,
        COUNT(f.id)                                           AS total_farmers,
        ROUND(100.0 * SUM(CASE WHEN f.gender='F' THEN 1 ELSE 0 END) / NULLIF(COUNT(f.id),0), 1) AS female_pct,
        ROUND(100.0 * SUM(CASE WHEN f.is_active THEN 1 ELSE 0 END)  / NULLIF(COUNT(f.id),0), 1) AS active_pct,
        ROUND(AVG(f.age), 1) AS avg_age
    FROM farmers f
    JOIN projects pr ON pr.id = f.project_id
    WHERE pr.project_country IN ({countries_str})
    AND   pr.project_year    IN ({years_str})
    GROUP BY pr.project_name, pr.project_country
    ORDER BY total_farmers DESC
    """
    df_fstats = q(farmer_stats_sql)

    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.markdown('<div class="section-header">Gender Breakdown</div>', unsafe_allow_html=True)
        if not df_gender.empty:
            fig = px.pie(
                df_gender, names="gender", values="count",
                hole=0.55,
                color="gender",
                color_discrete_map={"Female": "#E91E63", "Male": "#2196F3"},
                template="plotly_dark",
            )
            fig.update_layout(
                plot_bgcolor="#1a1f2e", paper_bgcolor="#1a1f2e",
                margin=dict(t=20, b=10, l=10, r=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1),
                height=320,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Per-Project Farmer Stats</div>', unsafe_allow_html=True)
        if not df_fstats.empty:
            df_fstats.columns = ["Project","Country","Total Farmers","Female %","Active %","Avg Age"]
            st.dataframe(df_fstats, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Data Quality":
    st.markdown("# 🔍 Data Quality")

    # Completeness bars
    st.markdown('<div class="section-header">Field Completeness</div>', unsafe_allow_html=True)

    completeness_sql = f"""
    SELECT
        'farmers.age'        AS field,
        ROUND(100.0 * COUNT(CASE WHEN f.age IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1) AS pct
    FROM farmers f JOIN projects pr ON pr.id = f.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    UNION ALL
    SELECT
        'farmers.gender',
        ROUND(100.0 * COUNT(CASE WHEN f.gender IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1)
    FROM farmers f JOIN projects pr ON pr.id = f.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    UNION ALL
    SELECT
        'parcels.area_parcel',
        ROUND(100.0 * COUNT(CASE WHEN p.area_parcel IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1)
    FROM parcels p JOIN projects pr ON pr.id = p.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    UNION ALL
    SELECT
        'parcels.area_to_plant',
        ROUND(100.0 * COUNT(CASE WHEN p.area_to_plant IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1)
    FROM parcels p JOIN projects pr ON pr.id = p.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    UNION ALL
    SELECT
        'parcels.number_of_tree',
        ROUND(100.0 * COUNT(CASE WHEN p.number_of_tree IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1)
    FROM parcels p JOIN projects pr ON pr.id = p.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    UNION ALL
    SELECT
        'parcel_visits.trees_alive',
        ROUND(100.0 * COUNT(CASE WHEN pv.trees_alive IS NOT NULL THEN 1 END) / NULLIF(COUNT(*),0), 1)
    FROM parcel_visits pv JOIN projects pr ON pr.id = pv.project_id
    WHERE pr.project_country IN ({countries_str}) AND pr.project_year IN ({years_str})
    """
    df_comp = q(completeness_sql)

    if not df_comp.empty:
        fig = px.bar(
            df_comp.sort_values("pct"), x="pct", y="field",
            orientation="h",
            text="pct",
            color="pct",
            color_continuous_scale=["#f44336","#FFC107","#4CAF50"],
            range_color=[0, 100],
            labels={"pct": "Completeness %", "field": "Field"},
            template="plotly_dark",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            plot_bgcolor="#1a1f2e", paper_bgcolor="#1a1f2e",
            margin=dict(t=20, b=10, l=20),
            xaxis=dict(range=[0, 110], gridcolor="#2d3447"),
            yaxis=dict(gridcolor="#2d3447"),
            coloraxis_showscale=False,
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Flag: area_to_plant > area_parcel
    st.markdown('<div class="section-header">⚠️ Parcels Where area_to_plant > area_parcel</div>', unsafe_allow_html=True)
    flag_area_sql = f"""
    SELECT
        p.parcel_name,
        pr.project_name,
        pr.project_country AS country,
        p.area_parcel,
        p.area_to_plant,
        ROUND(p.area_to_plant - p.area_parcel, 3) AS overage_ha
    FROM parcels p
    JOIN projects pr ON pr.id = p.project_id
    WHERE p.area_to_plant > p.area_parcel
    AND pr.project_country IN ({countries_str})
    AND pr.project_year    IN ({years_str})
    ORDER BY overage_ha DESC
    """
    df_flag = q(flag_area_sql)
    if df_flag.empty:
        st.success("✅ No parcels with area_to_plant > area_parcel found.")
    else:
        st.warning(f"Found {len(df_flag)} parcels with area mismatch:")
        st.dataframe(df_flag, use_container_width=True, hide_index=True)

    # Flag: farmers with missing age
    st.markdown('<div class="section-header">⚠️ Farmers with Missing Age</div>', unsafe_allow_html=True)
    flag_age_sql = f"""
    SELECT f.farmer_name, f.gender, pr.project_name, pr.project_country
    FROM farmers f
    JOIN projects pr ON pr.id = f.project_id
    WHERE f.age IS NULL
    AND pr.project_country IN ({countries_str})
    AND pr.project_year    IN ({years_str})
    """
    df_age = q(flag_age_sql)
    if df_age.empty:
        st.success("✅ No farmers with missing age.")
    else:
        st.warning(f"Found {len(df_age)} farmers with missing age:")
        st.dataframe(df_age, use_container_width=True, hide_index=True)
