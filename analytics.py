"""
Advanced analytics utilities for PUR monitoring data.

Provides tree survival analysis, farmer engagement metrics, carbon sequestration calculations,
and trend analysis for Nature-Based Solutions (NbS) projects.

Main classes:
    - PURAnalytics: Core analytics engine for project monitoring data

Typical usage:
    analytics = PURAnalytics("pur_monitor.db")
    survival_stats = analytics.get_tree_survival_stats()
    carbon = analytics.calculate_carbon_sequestration()
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import duckdb


class PURAnalytics:
    """
    Advanced analytics engine for PUR project data.
    
    Provides methods to calculate tree survival rates, farmer engagement metrics,
    carbon sequestration potential, and project progress tracking across
    multiple NbS initiatives.
    
    Attributes:
        db_path (str): Path to DuckDB database file
    """
    
    def __init__(self, db_path: str = "pur_monitor.db"):
        """
        Initialize analytics with database connection.
        
        Args:
            db_path: Path to DuckDB database file. If file doesn't exist,
                    will raise FileNotFoundError on first operation.
        
        Raises:
            TypeError: If db_path is not a string
        """
        if not isinstance(db_path, str):
            raise TypeError("db_path must be a string")
        if len(db_path) == 0:
            raise ValueError("db_path cannot be empty")
        
        self.db_path = db_path
    
    def get_tree_survival_stats(self) -> Dict:
        """
        Calculate tree survival statistics across all parcels (latest visit).
        
        Analyzes the most recent parcel visit for each parcel to determine
        overall tree survival rates and mortality across the portfolio.
        
        Returns:
            Dictionary containing:
                - total_parcels_visited (int): Number of unique parcels with visits
                - average_survival_rate (float): Mean survival rate (0-1 scale)
                - total_trees_alive (int): Total living trees in latest visits
                - total_trees_dead (int): Total dead trees in latest visits
                - overall_survival_percentage (float): Aggregate survival % (0-100)
        
        Edge cases:
            - Returns zeros if no parcel_visits exist in database
            - Excludes parcels with zero trees (divide-by-zero safe)
        
        Raises:
            Exception: If database connection fails
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        try:
            result = con.execute("""
                SELECT
                    COUNT(DISTINCT p.parcel_id) as total_parcels,
                    ROUND(AVG(pv.trees_alive::FLOAT / 
                        NULLIF(pv.trees_alive + pv.trees_dead, 0)), 3) as avg_survival_rate,
                    SUM(pv.trees_alive) as total_trees_alive,
                    SUM(pv.trees_dead) as total_trees_dead,
                    ROUND(100.0 * SUM(pv.trees_alive) / 
                        NULLIF(SUM(pv.trees_alive) + SUM(pv.trees_dead), 0), 1) as overall_survival_pct
                FROM parcel_visits pv
                INNER JOIN (
                    SELECT parcel_id, MAX(visit_date) as last_visit
                    FROM parcel_visits
                    GROUP BY parcel_id
                ) p ON pv.parcel_id = p.parcel_id AND pv.visit_date = p.last_visit
            """).fetchone()
            
            return {
                "total_parcels_visited": result[0] or 0,
                "average_survival_rate": result[1] or 0.0,
                "total_trees_alive": result[2] or 0,
                "total_trees_dead": result[3] or 0,
                "overall_survival_percentage": result[4] or 0.0,
            }
        finally:
            con.close()
    
    def get_farmer_engagement_metrics(self) -> Dict:
        """
        Calculate farmer engagement metrics including active rates and gender balance.
        
        Analyzes farmer status (active/inactive) and gender distribution
        across all projects to assess team capacity and diversity.
        
        Returns:
            Dictionary containing:
                - total_farmers (int): Total farmer count
                - active_farmers (int): Farmers marked as active
                - engagement_rate_pct (float): % of active farmers (0-100)
                - female_farmers (int): Count of female farmers
                - male_farmers (int): Count of male farmers
                - female_ratio_pct (float): % female farmers (0-100)
        
        Edge cases:
            - Returns zeros if farmers table is empty
            - Gender counts may not sum to total if gender='Other' or NULL exist
        
        Raises:
            Exception: If database connection fails
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        try:
            result = con.execute("""
                SELECT
                    COUNT(*) as total_farmers,
                    SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_farmers,
                    ROUND(100.0 * SUM(CASE WHEN is_active THEN 1 ELSE 0 END) / 
                        NULLIF(COUNT(*), 0), 1) as engagement_rate,
                    SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as female_farmers,
                    SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) as male_farmers
                FROM farmers
            """).fetchone()
            
            total = result[0] or 0
            female_count = result[3] or 0
            
            return {
                "total_farmers": total,
                "active_farmers": result[1] or 0,
                "engagement_rate_pct": result[2] or 0.0,
                "female_farmers": female_count,
                "male_farmers": result[4] or 0,
                "female_ratio_pct": round(100.0 * female_count / max(total, 1), 1),
            }
        finally:
            con.close()
    
    def get_project_status_summary(self) -> List[Dict]:
        """
        Get status summary for each project.
        
        Returns detailed metrics per project including farmer counts,
        parcel counts, and tree/area targets.
        
        Returns:
            List of dictionaries (ordered by farmer_count DESC) containing:
                - project_id (int): Unique project identifier
                - project_name (str): Project name
                - country (str): 2-letter country code (BR, CO, PE, MX)
                - farmer_count (int): Number of active farmers
                - parcel_count (int): Number of land parcels
                - trees_planned (int): Total trees to be planted
                - area_planned_ha (float): Total area in hectares
        
        Edge cases:
            - Returns empty list if projects table is empty
            - Counts are 0 if no farmers/parcels exist for project
        
        Raises:
            Exception: If database connection fails
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        try:
            results = con.execute("""
                SELECT
                    p.id,
                    p.name,
                    p.country,
                    COUNT(DISTINCT f.id) as farmer_count,
                    COUNT(DISTINCT pc.id) as parcel_count,
                    COALESCE(SUM(pc.number_of_tree), 0) as trees_planned,
                    COALESCE(SUM(pc.area_to_plant), 0) as area_planned_ha
                FROM projects p
                LEFT JOIN farmers f ON p.id = f.project_id
                LEFT JOIN parcels pc ON f.id = pc.farmer_id
                GROUP BY p.id, p.name, p.country
                ORDER BY farmer_count DESC
            """).fetchall()
            
            return [
                {
                    "project_id": r[0],
                    "project_name": r[1],
                    "country": r[2],
                    "farmer_count": r[3] or 0,
                    "parcel_count": r[4] or 0,
                    "trees_planned": r[5] or 0,
                    "area_planned_ha": round(r[6] or 0.0, 2),
                }
                for r in results
            ]
        finally:
            con.close()
    
    def calculate_planting_completion_rate(self, days_back: int = 30) -> float:
        """
        Calculate percentage of planned planting completed in past N days.
        
        Args:
            days_back: Number of days to look back (default: 30)
            
        Returns:
            Completion rate as percentage (0-100)
            
        Raises:
            ValueError: If days_back is negative or > 3650
        """
        if not isinstance(days_back, int) or days_back < 0 or days_back > 3650:
            raise ValueError("days_back must be 0-3650 (0-10 years)")
        
        con = duckdb.connect(self.db_path, read_only=True)
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
            
            result = con.execute(f"""
                SELECT
                    ROUND(100.0 * COUNT(DISTINCT pv.parcel_id) / 
                        NULLIF(COUNT(DISTINCT pc.id), 0), 1)
                FROM parcels pc
                LEFT JOIN parcel_visits pv ON pc.id = pv.parcel_id 
                    AND pv.visit_date >= '{cutoff_date}'
            """).fetchone()
            
            return result[0] if result[0] is not None else 0.0
        finally:
            con.close()
    
    def calculate_carbon_sequestration(self, tree_species_carbon_map: Optional[Dict[str, float]] = None) -> Dict:
        """
        Calculate carbon sequestration potential based on alive trees.
        
        Tree carbon sequestration rates (kg CO2/year):
        - Native species (avg): 15 kg CO2/year
        - Reforestation species: 12 kg CO2/year
        - Agroforestry species: 20 kg CO2/year
        
        Args:
            tree_species_carbon_map: Optional dict mapping species to CO2 sequestration (kg/year)
                                    Default uses species-neutral average of 15 kg/year
        
        Returns:
            Dictionary with:
                - total_trees_alive: Sum of living trees
                - avg_annual_carbon_kg: Annual CO2 sequestration (kg)
                - avg_annual_carbon_tonnes: Annual CO2 sequestration (tonnes)
                - 10_year_projection_tonnes: 10-year projection
                - 30_year_projection_tonnes: 30-year projection
        
        Raises:
            ValueError: If tree_species_carbon_map contains non-positive values
        """
        if tree_species_carbon_map is None:
            # Default: 15 kg CO2/tree/year (conservative NbS average)
            default_rate = 15.0
        else:
            if not all(v > 0 for v in tree_species_carbon_map.values()):
                raise ValueError("Carbon rates must be positive")
            default_rate = sum(tree_species_carbon_map.values()) / len(tree_species_carbon_map)
        
        con = duckdb.connect(self.db_path, read_only=True)
        
        try:
            result = con.execute("""
                SELECT COALESCE(SUM(trees_alive), 0)
                FROM parcel_visits
                WHERE visit_date = (SELECT MAX(visit_date) FROM parcel_visits)
            """).fetchone()
            
            total_alive = result[0] or 0
            annual_carbon_kg = total_alive * default_rate
            annual_carbon_tonnes = annual_carbon_kg / 1000.0
            
            return {
                "total_trees_alive": total_alive,
                "avg_annual_carbon_kg": round(annual_carbon_kg, 1),
                "avg_annual_carbon_tonnes": round(annual_carbon_tonnes, 2),
                "10_year_projection_tonnes": round(annual_carbon_tonnes * 10, 2),
                "30_year_projection_tonnes": round(annual_carbon_tonnes * 30, 2),
            }
        finally:
            con.close()

    def calculate_survival_trend(
        self,
        window_visits: int = 3,
    ) -> dict:
        """
        Analyse tree survival rate trend over the last N visits per parcel.

        Identifies whether the portfolio is improving, stable, or declining
        by comparing average survival rates across consecutive visit cohorts.

        Args:
            window_visits: Number of most-recent visits per parcel to include (default 3)

        Returns:
            Dict with:
                - trend_direction: "improving", "stable", or "declining"
                - avg_survival_first_visit_pct: Average survival in earliest included visit
                - avg_survival_latest_visit_pct: Average survival in most-recent visit
                - change_pct_points: Latest minus earliest (positive = improving)
                - parcels_analyzed: Number of parcels with enough visit history
                - window_visits: Visit window used

        Raises:
            ValueError: If window_visits < 2

        Example:
            >>> analytics = PURAnalytics("pur_monitor.db")
            >>> trend = analytics.calculate_survival_trend(window_visits=3)
            >>> print(f"Trend: {trend['trend_direction']} ({trend['change_pct_points']:+.1f} pp)")
        """
        if window_visits < 2:
            raise ValueError("window_visits must be at least 2")

        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Get ranked visits per parcel (most recent = rank 1)
            rows = con.execute(f"""
                WITH ranked AS (
                    SELECT
                        pv.parcel_id,
                        pv.trees_alive,
                        pc.number_of_tree AS trees_planned,
                        ROW_NUMBER() OVER (PARTITION BY pv.parcel_id ORDER BY pv.visit_date DESC) AS rn
                    FROM parcel_visits pv
                    JOIN parcels pc ON pv.parcel_id = pc.id
                    WHERE pc.number_of_tree > 0
                )
                SELECT parcel_id, trees_alive, trees_planned, rn
                FROM ranked
                WHERE rn <= {window_visits}
                ORDER BY parcel_id, rn
            """).fetchall()
        finally:
            con.close()

        if not rows:
            return {
                "trend_direction": "unknown",
                "parcels_analyzed": 0,
                "window_visits": window_visits,
                "change_pct_points": 0.0,
            }

        # Aggregate by parcel: compare first vs last in window
        from collections import defaultdict
        parcel_visits: dict = defaultdict(list)
        for parcel_id, alive, planned, rn in rows:
            survival = (alive / planned * 100) if planned > 0 else 0.0
            parcel_visits[parcel_id].append((rn, survival))

        first_survivals = []
        latest_survivals = []
        for parcel_id, visits in parcel_visits.items():
            if len(visits) < 2:
                continue
            visits_sorted = sorted(visits, key=lambda x: x[0])  # oldest first (highest rn)
            first_survivals.append(visits_sorted[0][1])
            latest_survivals.append(visits_sorted[-1][1])

        if not first_survivals:
            return {
                "trend_direction": "insufficient_data",
                "parcels_analyzed": 0,
                "window_visits": window_visits,
                "change_pct_points": 0.0,
            }

        avg_first = sum(first_survivals) / len(first_survivals)
        avg_latest = sum(latest_survivals) / len(latest_survivals)
        change = avg_latest - avg_first

        if change > 2.0:
            direction = "improving"
        elif change < -2.0:
            direction = "declining"
        else:
            direction = "stable"

        return {
            "trend_direction": direction,
            "avg_survival_first_visit_pct": round(avg_first, 1),
            "avg_survival_latest_visit_pct": round(avg_latest, 1),
            "change_pct_points": round(change, 2),
            "parcels_analyzed": len(first_survivals),
            "window_visits": window_visits,
        }

    def get_top_mortality_parcels(
        self,
        top_n: int = 5,
        min_trees_planned: int = 10,
    ) -> list:
        """
        Return parcels with the highest tree mortality in the latest visit.

        Args:
            top_n: Number of worst-performing parcels to return (default 5)
            min_trees_planned: Minimum trees planned to include parcel (default 10)

        Returns:
            List of dicts with parcel_id, farmer_name, trees_planned,
            trees_alive, mortality_rate_pct, and latest_visit_date

        Raises:
            ValueError: If top_n < 1

        Example:
            >>> worst = analytics.get_top_mortality_parcels(top_n=10)
            >>> for p in worst:
            ...     print(f"{p['parcel_id']}: {p['mortality_rate_pct']:.1f}% mortality")
        """
        if top_n < 1:
            raise ValueError("top_n must be at least 1")

        con = duckdb.connect(self.db_path, read_only=True)
        try:
            rows = con.execute(f"""
                WITH latest_visits AS (
                    SELECT pv.parcel_id,
                           pv.trees_alive,
                           pv.visit_date,
                           ROW_NUMBER() OVER (PARTITION BY pv.parcel_id ORDER BY pv.visit_date DESC) AS rn
                    FROM parcel_visits pv
                ),
                latest AS (
                    SELECT * FROM latest_visits WHERE rn = 1
                )
                SELECT
                    pc.id            AS parcel_id,
                    f.name           AS farmer_name,
                    pc.number_of_tree AS trees_planned,
                    lv.trees_alive,
                    lv.visit_date,
                    ROUND(100.0 * (pc.number_of_tree - lv.trees_alive) / NULLIF(pc.number_of_tree, 0), 1) AS mortality_pct
                FROM parcels pc
                JOIN farmers f ON pc.farmer_id = f.id
                JOIN latest lv ON pc.id = lv.parcel_id
                WHERE pc.number_of_tree >= {min_trees_planned}
                ORDER BY mortality_pct DESC
                LIMIT {top_n}
            """).fetchall()
        finally:
            con.close()

        return [
            {
                "parcel_id": r[0],
                "farmer_name": r[1],
                "trees_planned": r[2],
                "trees_alive": r[3],
                "latest_visit_date": str(r[4]),
                "mortality_rate_pct": r[5],
            }
            for r in rows
        ]
