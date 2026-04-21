import sys, os
sys.path.append(os.path.abspath('backend'))
from backend.db.session import SessionLocal
from backend.app.main import get_perfect_parlay
try:
    db = SessionLocal()
    res = get_perfect_parlay(db)
    print("Parlay results:", res)
except Exception as e:
    print(f"ERROR: {e}")
