import sys
import os
from sqlalchemy import text

# Set python path to backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import engine, Base
from db.models import User, Bet # Ensure models are imported for create_all

def migrate_auth():
    print("--- Starting Auth Migration ---")
    
    # 1. Create new tables (like 'users')
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created/verified.")

    # 2. Manually add user_id column to bets if it doesn't exist
    print("Updating 'bets' table...")
    with engine.connect() as conn:
        # Check if user_id column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='bets' AND column_name='user_id'
        """))
        if not result.fetchone():
            print("Adding 'user_id' column to 'bets' table...")
            conn.execute(text("ALTER TABLE bets ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            conn.commit()
            print("Column 'user_id' added successfully.")
        else:
            print("Column 'user_id' already exists in 'bets' table.")
            
    print("--- Auth Migration Complete ---")

if __name__ == "__main__":
    migrate_auth()
