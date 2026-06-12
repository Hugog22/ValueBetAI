from db.session import SessionLocal
from db.models import Bet, Match, User
db = SessionLocal()
all_bets = db.query(Bet, Match).join(Match, Bet.match_id == Match.id).all()
seen = set()
for bet, match in all_bets:
    sig = (bet.user_id, bet.match_id, bet.market, bet.selection)
    if sig in seen:
        print(f"DUPLICATE DETECTED IN DB: id={bet.id}, match={bet.match_id}, sig={sig}")
    else:
        seen.add(sig)
print(f"Total rows: {len(all_bets)}, Unique: {len(seen)}")
