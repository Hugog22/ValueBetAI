from db.session import SessionLocal
from db.models import Team
db = SessionLocal()
teams = db.query(Team).all()
for t in teams[:10]:
    print(f"{t.name}: api_football_id={t.api_football_id}")
