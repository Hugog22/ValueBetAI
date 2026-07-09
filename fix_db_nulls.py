from backend.db.session import SessionLocal
from backend.db.models import User

db = SessionLocal()
try:
    users = db.query(User).filter(User.is_admin == None).all()
    for u in users:
        u.is_admin = False
    db.commit()
    print(f"Fixed {len(users)} users.")
finally:
    db.close()
