"""
Additional test suite for pur-monitor enhancements.
"""

import pytest
import tempfile
import duckdb
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        con = duckdb.connect(str(db_path))
        
        # Create minimal schema
        con.execute("""
            CREATE TABLE projects (
                id VARCHAR,
                name VARCHAR,
                country VARCHAR,
                status VARCHAR
            )
        """)
        
        con.execute("""
            CREATE TABLE farmers (
                id VARCHAR,
                gender VARCHAR,
                is_active BOOLEAN,
                project_id VARCHAR
            )
        """)
        
        con.execute("""
            CREATE TABLE parcels (
                id VARCHAR,
                farmer_id VARCHAR,
                area_to_plant DECIMAL,
                number_of_tree INTEGER,
                is_active BOOLEAN
            )
        """)
        
        con.execute("""
            CREATE TABLE parcel_visits (
                parcel_id VARCHAR,
                visit_date DATE,
                trees_alive INTEGER,
                trees_dead INTEGER
            )
        """)
        
        yield con, str(db_path)
        con.close()


class TestDatabaseSchema:
    """Test database schema and integrity."""
    
    def test_schema_exists(self, temp_db):
        """Test that all required tables exist."""
        con, _ = temp_db
        tables = con.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()
        
        table_names = [t[0] for t in tables]
        assert "projects" in table_names
        assert "farmers" in table_names
        assert "parcels" in table_names
    
    def test_insert_project(self, temp_db):
        """Test inserting a project."""
        con, _ = temp_db
        con.execute("""
            INSERT INTO projects (id, name, country, status)
            VALUES ('PRJ-001', 'Test Project', 'Indonesia', 'active')
        """)
        
        result = con.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        assert result == 1
    
    def test_insert_farmer(self, temp_db):
        """Test inserting a farmer."""
        con, _ = temp_db
        con.execute("INSERT INTO projects VALUES ('PRJ-001', 'Test', 'ID', 'active')")
        con.execute("""
            INSERT INTO farmers (id, gender, is_active, project_id)
            VALUES ('F-001', 'F', true, 'PRJ-001')
        """)
        
        result = con.execute("SELECT COUNT(*) FROM farmers").fetchone()[0]
        assert result == 1


class TestAnalytics:
    """Test analytics queries."""
    
    def test_active_farmers_count(self, temp_db):
        """Test counting active farmers."""
        con, _ = temp_db
        con.execute("INSERT INTO projects VALUES ('PRJ-001', 'Test', 'ID', 'active')")
        con.execute("""
            INSERT INTO farmers VALUES ('F-001', 'M', true, 'PRJ-001')
        """)
        con.execute("""
            INSERT INTO farmers VALUES ('F-002', 'F', false, 'PRJ-001')
        """)
        
        result = con.execute(
            "SELECT COUNT(*) FROM farmers WHERE is_active"
        ).fetchone()[0]
        assert result == 1
    
    def test_gender_distribution(self, temp_db):
        """Test gender distribution query."""
        con, _ = temp_db
        con.execute("INSERT INTO projects VALUES ('PRJ-001', 'Test', 'ID', 'active')")
        con.execute("""
            INSERT INTO farmers VALUES ('F-001', 'F', true, 'PRJ-001')
        """)
        con.execute("""
            INSERT INTO farmers VALUES ('F-002', 'F', true, 'PRJ-001')
        """)
        con.execute("""
            INSERT INTO farmers VALUES ('F-003', 'M', true, 'PRJ-001')
        """)
        
        result = con.execute("""
            SELECT gender, COUNT(*) as count
            FROM farmers
            GROUP BY gender
            ORDER BY count DESC
        """).fetchall()
        
        assert len(result) == 2
        assert result[0][1] == 2  # Female count


class TestTreePlanting:
    """Test tree planting metrics."""
    
    def test_total_trees_planned(self, temp_db):
        """Test calculating total trees planned."""
        con, _ = temp_db
        con.execute("""
            INSERT INTO parcels VALUES
            ('P-001', 'F-001', 1.0, 100, true),
            ('P-002', 'F-002', 2.0, 200, true)
        """)
        
        result = con.execute(
            "SELECT SUM(number_of_tree) FROM parcels WHERE is_active"
        ).fetchone()[0]
        assert result == 300
    
    def test_tree_survival_rate(self, temp_db):
        """Test calculating tree survival rate."""
        con, _ = temp_db
        con.execute("INSERT INTO parcels VALUES ('P-001', 'F-001', 1.0, 100, true)")
        con.execute("""
            INSERT INTO parcel_visits VALUES ('P-001', '2025-01-01', 95, 5)
        """)
        
        result = con.execute("""
            SELECT
                trees_alive,
                trees_dead,
                ROUND(100.0 * trees_alive / (trees_alive + trees_dead), 1) AS survival_rate
            FROM parcel_visits
            WHERE parcel_id = 'P-001'
        """).fetchone()
        
        assert result[2] == 95.0  # Survival rate
