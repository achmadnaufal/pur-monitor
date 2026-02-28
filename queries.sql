-- ============================================================
-- PUR Latin America Monitoring — Core SQL Views
-- queries.sql
-- Run against: pur_monitor.db (DuckDB)
-- Usage example:
--   duckdb pur_monitor.db < queries.sql
--   duckdb pur_monitor.db "SELECT * FROM v_latam_monitoring"
-- ============================================================

-- ------------------------------------------------------------
-- VIEW: v_latam_monitoring
-- Per-project KPI rollup: farmers, parcels, trees alive,
-- area planted, and % achievement vs. targets.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_latam_monitoring AS
WITH latest_visits AS (
    SELECT
        v.project_id,
        v.parcel_id,
        v.trees_alive,
        v.trees_dead
    FROM parcel_visits v
    INNER JOIN (
        SELECT parcel_id, MAX(visit_date) AS last_date
        FROM parcel_visits
        GROUP BY parcel_id
    ) lv ON v.parcel_id = lv.parcel_id AND v.visit_date = lv.last_date
),
parcel_stats AS (
    SELECT
        project_id,
        COUNT(*)              FILTER (WHERE is_active) AS active_parcels,
        SUM(area_to_plant)    FILTER (WHERE is_active) AS area_ha_planned,
        SUM(number_of_tree)   FILTER (WHERE is_active) AS trees_planned
    FROM parcels
    GROUP BY project_id
),
visit_agg AS (
    SELECT
        project_id,
        SUM(trees_alive) AS trees_alive,
        SUM(trees_dead)  AS total_trees_dead
    FROM latest_visits
    GROUP BY project_id
),
farmer_stats AS (
    SELECT
        project_id,
        COUNT(*)                        AS total_farmers,
        COUNT(*) FILTER (WHERE is_active) AS active_farmers
    FROM farmers
    GROUP BY project_id
)
SELECT
    p.id                                      AS project_id,
    p.project_name,
    p.project_country,
    p.project_year,
    c.country_code,

    -- Farmers
    COALESCE(fs.total_farmers,  0)            AS total_farmers,
    COALESCE(fs.active_farmers, 0)            AS active_farmers,
    pt.target_farmers,
    ROUND(100.0 * COALESCE(fs.active_farmers,0) / NULLIF(pt.target_farmers, 0), 1)
                                              AS pct_farmers_achieved,

    -- Parcels
    COALESCE(ps.active_parcels, 0)            AS active_parcels,
    pt.target_parcels,
    ROUND(100.0 * COALESCE(ps.active_parcels,0) / NULLIF(pt.target_parcels, 0), 1)
                                              AS pct_parcels_achieved,

    -- Trees
    COALESCE(ps.trees_planned,  0)            AS trees_planned,
    COALESCE(va.trees_alive,    0)            AS trees_alive,
    COALESCE(va.total_trees_dead, 0)          AS trees_dead_all_visits,
    pt.target_trees,
    ROUND(100.0 * COALESCE(va.trees_alive,0) / NULLIF(pt.target_trees, 0), 1)
                                              AS pct_trees_achieved,

    -- Area
    ROUND(COALESCE(ps.area_ha_planned, 0), 2) AS area_ha_planted,
    pt.target_area_hectares,
    ROUND(100.0 * COALESCE(ps.area_ha_planned,0) / NULLIF(pt.target_area_hectares, 0), 1)
                                              AS pct_area_achieved,

    -- Timeline
    pt.start_date,
    pt.end_date

FROM projects p
LEFT JOIN countries       c  ON c.id  = p.country_id
LEFT JOIN project_targets pt ON pt.project_id = p.id
LEFT JOIN parcel_stats    ps ON ps.project_id = p.id
LEFT JOIN visit_agg       va ON va.project_id = p.id
LEFT JOIN farmer_stats    fs ON fs.project_id = p.id
ORDER BY p.id;


-- ------------------------------------------------------------
-- VIEW: v_mortality_analysis
-- Mortality cause breakdown: visits, trees lost, share.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_mortality_analysis AS
WITH visit_mortality AS (
    SELECT
        pv.project_id,
        pv.mortality_id,
        COUNT(*)         AS visit_count,
        SUM(pv.trees_dead) AS trees_dead
    FROM parcel_visits pv
    WHERE pv.trees_dead > 0
    GROUP BY pv.project_id, pv.mortality_id
),
global_totals AS (
    SELECT
        mortality_id,
        SUM(visit_count) AS total_visits,
        SUM(trees_dead)  AS total_trees_dead
    FROM visit_mortality
    GROUP BY mortality_id
)
SELECT
    rm.id                AS mortality_id,
    rm.mortality_name,
    gt.total_visits,
    gt.total_trees_dead,
    ROUND(100.0 * gt.total_trees_dead / NULLIF(SUM(gt.total_trees_dead) OVER (), 0), 2)
                         AS pct_of_total_dead,
    RANK() OVER (ORDER BY gt.total_trees_dead DESC) AS rank_by_trees_dead
FROM global_totals gt
JOIN ref_mortality rm ON rm.id = gt.mortality_id
ORDER BY rank_by_trees_dead;


-- ------------------------------------------------------------
-- VIEW: v_farmer_demographics
-- Gender breakdown, age stats, active rate — per project.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW v_farmer_demographics AS
SELECT
    p.id             AS project_id,
    p.project_name,
    p.project_country,
    COUNT(*)                                        AS total_farmers,
    COUNT(*) FILTER (WHERE f.gender = 'F')          AS female_count,
    COUNT(*) FILTER (WHERE f.gender = 'M')          AS male_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE f.gender = 'F') / NULLIF(COUNT(*), 0), 1)
                                                    AS pct_female,
    COUNT(*) FILTER (WHERE f.is_active)             AS active_farmers,
    ROUND(100.0 * COUNT(*) FILTER (WHERE f.is_active) / NULLIF(COUNT(*), 0), 1)
                                                    AS pct_active,
    ROUND(AVG(f.age), 1)                            AS avg_age,
    MIN(f.age)                                      AS min_age,
    MAX(f.age)                                      AS max_age
FROM farmers f
JOIN projects p ON p.id = f.project_id
GROUP BY p.id, p.project_name, p.project_country
ORDER BY p.id;
