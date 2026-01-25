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
