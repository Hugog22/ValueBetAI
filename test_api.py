import sys
import os
sys.path.append(os.path.abspath('backend'))
from backend.db.session import SessionLocal
from backend.app.main import get_jornada

db = SessionLocal()
try:
    matches = get_jornada(db)
    print(f"Total returned by API: {len(matches)}")
    for m in matches:
        bp = m.get('bestPick', {})
        print(f"Match: {m['homeTeam']} vs {m['awayTeam']} | EV: {bp.get('ev')} | Risk: {bp.get('risk', {}).get('level')}")
except Exception as e:
    print(f"ERROR: {e}")
