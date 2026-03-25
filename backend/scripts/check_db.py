import sys
import os

# Set python path to backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import Match, Team, OddsHistory
from sqlalchemy import func

def check_db():
    db = SessionLocal()
    try:
        match_count = db.query(func.count(Match.id)).scalar()
        team_count = db.query(func.count(Team.id)).scalar()
        odds_history_count = db.query(func.count(OddsHistory.id)).scalar()
        
        print("--- Database Diagnostic ---")
        print(f"Teams: {team_count}")
        print(f"Matches: {match_count}")
        print(f"Odds History: {odds_history_count}")
        print("---------------------------")
        
        if match_count == 0:
            print("WARNING: The matches table is empty. Data needs to be reloaded.")
        else:
            print("Matches found. If they are not appearing in the frontend, check the status and date filters.")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
