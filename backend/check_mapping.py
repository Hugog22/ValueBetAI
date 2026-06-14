from db.session import SessionLocal
from db.models import Match, Team
db = SessionLocal()
matches = db.query(Match).filter(Match.id.in_([542, 22])).all()
for m in matches:
    print(f"Match {m.id} | Date: {m.date} | Home: {m.home_team.name} | Away: {m.away_team.name} | API ID: {m.api_football_id}")
