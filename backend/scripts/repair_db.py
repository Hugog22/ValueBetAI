from app.main import app
from db.session import engine, Base, SessionLocal
from db.models import Match, Team, User
from datetime import datetime, timedelta
import random

def repair():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Check if 'users' table is empty/works
        count = db.query(User).count()
        print(f"Users in DB: {count}")
        
        # 2. Update matches to be in the future
        matches = db.query(Match).all()
        print(f"Updating {len(matches)} matches to future dates...")
        now = datetime.utcnow()
        for idx, m in enumerate(matches):
            # Spread matches over the next 7 days
            days_out = (idx % 7)
            hours_out = (idx % 24)
            m.date = now + timedelta(days=days_out, hours=hours_out)
            m.status = "Not Started"
        
        db.commit()
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    repair()
