from db.session import SessionLocal
from db.models import Bet
db = SessionLocal()
# Delete all system bets we just placed
db.query(Bet).filter(Bet.user_id == None).delete()
db.commit()
print("System bets deleted.")
