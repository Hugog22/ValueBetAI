from db.session import SessionLocal
from db.models import Match
db = SessionLocal()
m = db.query(Match).filter(Match.id == 22).first()
print(f"Match 22 date: {m.date}")
