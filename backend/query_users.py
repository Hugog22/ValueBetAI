from db.session import SessionLocal
from db.models import User
db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(u.id, u.email)
preds = 0
print("Total predictions with value_bet_flag=True:", preds)
