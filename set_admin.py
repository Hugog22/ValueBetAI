from backend.db.session import SessionLocal
from backend.db.models import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "hugodesax123@gmail.com").first()
    if user:
        user.is_admin = True
        db.commit()
        print(f"Successfully updated user {user.email} to admin.")
    else:
        print("User not found.")
finally:
    db.close()
