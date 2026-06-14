import httpx
from db.session import SessionLocal
from db.models import Match
from core.config import settings

db = SessionLocal()
matches = db.query(Match).filter(Match.id.in_([542, 22])).all()
for m in matches:
    print(f"Match {m.id}: api_football_id={m.api_football_id}")
    if m.api_football_id:
        resp = httpx.get(
            "https://v3.football.api-sports.io/fixtures/players",
            headers={"x-apisports-key": settings.API_SPORTS_KEY},
            params={"fixture": m.api_football_id}
        )
        print(f"Fixture data length: {len(resp.json().get('response', []))}")
        print(resp.json())
