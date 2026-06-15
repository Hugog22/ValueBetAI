import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

from db.models import Match

print("=== Counting matches per team ===")
matches = session.query(Match).filter(Match.stage == 'group_stage').all()
team_counts = {}
for m in matches:
    h = m.home_team.name
    a = m.away_team.name
    team_counts[h] = team_counts.get(h, 0) + 1
    team_counts[a] = team_counts.get(a, 0) + 1

for t, c in sorted(team_counts.items(), key=lambda x: x[1]):
    if c != 3:
        print(f"Team {t} has {c} matches!")

print("If nothing printed above, all teams have exactly 3 matches.")

