from db.session import SessionLocal
from db.models import Bet, Match, User
db = SessionLocal()
all_bets = db.query(Bet, Match).join(Match, Bet.match_id == Match.id).all()
for bet, match in all_bets:
    sig = (bet.user_id, bet.match_id, bet.market, bet.selection)
    print(f"Bet id={bet.id}, match={bet.match_id}, user={bet.user_id}, market={bet.market}, selection={bet.selection}, status={bet.status}")
