"""
Advanced analytics utilities for PUR monitoring data.

Provides tree survival analysis, farmer engagement metrics, and trend calculations.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import duckdb


class PURAnalytics:
    """Advanced analytics for PUR project data."""
    
    def __init__(self, db_path: str = "pur_monitor.db"):
        """
        Initialize analytics with database connection.
        
        Args:
            db_path: Path to DuckDB database
        """
        self.db_path = db_path
    
    def get_tree_survival_stats(self) -> Dict:
        """
        Calculate tree survival statistics across all parcels.
        
        Returns:
            Dictionary with survival metrics
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        result = con.execute("""
            SELECT
                COUNT(DISTINCT p.parcel_id) as total_parcels,
                ROUND(AVG(pv.trees_alive::FLOAT / 
                    (pv.trees_alive + pv.trees_dead)), 3) as avg_survival_rate,
                SUM(pv.trees_alive) as total_trees_alive,
                SUM(pv.trees_dead) as total_trees_dead,
                ROUND(100.0 * SUM(pv.trees_alive) / 
                    (SUM(pv.trees_alive) + SUM(pv.trees_dead)), 1) as overall_survival_pct
            FROM parcel_visits pv
            INNER JOIN (
                SELECT parcel_id, MAX(visit_date) as last_visit
                FROM parcel_visits
                GROUP BY parcel_id
            ) p ON pv.parcel_id = p.parcel_id AND pv.visit_date = p.last_visit
        """).fetchone()
        
        con.close()
        
        return {
            "total_parcels_visited": result[0] or 0,
            "average_survival_rate": result[1] or 0.0,
            "total_trees_alive": result[2] or 0,
            "total_trees_dead": result[3] or 0,
            "overall_survival_percentage": result[4] or 0.0,
        }
    
    def get_farmer_engagement_metrics(self) -> Dict:
        """
        Calculate farmer engagement metrics including active rates and gender balance.
        
        Returns:
            Dictionary with engagement metrics
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        result = con.execute("""
            SELECT
                COUNT(*) as total_farmers,
                SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_farmers,
                ROUND(100.0 * SUM(CASE WHEN is_active THEN 1 ELSE 0 END) / 
                    COUNT(*), 1) as engagement_rate,
                SUM(CASE WHEN gender = 'F' THEN 1 ELSE 0 END) as female_farmers,
                SUM(CASE WHEN gender = 'M' THEN 1 ELSE 0 END) as male_farmers
            FROM farmers
        """).fetchone()
        
        con.close()
        
        return {
            "total_farmers": result[0] or 0,
            "active_farmers": result[1] or 0,
            "engagement_rate_pct": result[2] or 0.0,
            "female_farmers": result[3] or 0,
            "male_farmers": result[4] or 0,
            "female_ratio_pct": round(100.0 * (result[3] or 0) / (result[0] or 1), 1),
        }
    
    def get_project_status_summary(self) -> List[Dict]:
        """
        Get status summary for each project.
        
        Returns:
            List of dictionaries with project metrics
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
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
        
        con.close()
        
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
    
    def calculate_planting_completion_rate(self, days_back: int = 30) -> float:
        """
        Calculate percentage of planned planting completed in past N days.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Completion rate as percentage
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        result = con.execute(f"""
            SELECT
                ROUND(100.0 * COUNT(DISTINCT pv.parcel_id) / 
                    NULLIF(COUNT(DISTINCT pc.id), 0), 1)
            FROM parcels pc
            LEFT JOIN parcel_visits pv ON pc.id = pv.parcel_id 
                AND pv.visit_date >= '{cutoff_date}'
        """).fetchone()
        
        con.close()
        
        return result[0] if result[0] is not None else 0.0
