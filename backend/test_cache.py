from core.cache_service import refresh_cache
import logging
logging.basicConfig(level=logging.INFO)
refresh_cache()

from db.session import SessionLocal
from db.models import Bet
db = SessionLocal()
sys_bets = db.query(Bet).filter(Bet.user_id == None).all()
print(f"Total system bets automatically placed: {len(sys_bets)}")
for b in sys_bets:
    print(f"System Bet: match={b.match_id}, market={b.market}, selection={b.selection}, odds={b.odds_taken}, stake={b.stake}")
