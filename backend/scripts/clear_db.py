"""
Script to clear stale data from the database.
Deletes all records from predictions, odds, matches, and teams tables
so the ETL pipeline can repopulate with current season data.

Usage:
    cd backend
    python -m scripts.clear_db
"""

import sys
import os

# Ensure the backend directory is in the path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.session import engine, Base
from db.models import Prediction, Odds, Match, Team

def clear_database():
    """Delete all records from predictions, odds, matches, and teams tables."""
    print("⚠️  Clearing all data from the database...")

    with engine.connect() as conn:
        # Delete in order to respect foreign key constraints
        tables = [
            ("predictions", Prediction.__tablename__),
            ("odds", Odds.__tablename__),
            ("matches", Match.__tablename__),
            ("teams", Team.__tablename__),
        ]

        for label, table_name in tables:
            result = conn.execute(text(f"DELETE FROM {table_name}"))
            print(f"   🗑️  Deleted {result.rowcount} rows from '{table_name}'")

        conn.commit()

    print("✅ Database cleared successfully. Ready for fresh data.")

if __name__ == "__main__":
    clear_database()
