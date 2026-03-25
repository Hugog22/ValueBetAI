import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect
from db.session import engine, Base
from db.models import MarketOdds, Odds, Match, Team, Prediction # Import all to assure they are registered

def migrate():
    print("Running migration to create new tables...")
    # create_all only generates tables that do not exist yet. Safe for existing data.
    Base.metadata.create_all(bind=engine)
    print("Migration finished! DB schema is up to date.")

if __name__ == "__main__":
    migrate()
