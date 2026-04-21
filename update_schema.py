import sys, os
sys.path.append(os.path.abspath('backend'))
from backend.db.session import engine
from sqlalchemy import text

with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN bankroll FLOAT DEFAULT 1000.0;"))
        print("Column bankroll added to users table successfully.")
    except Exception as e:
        print(f"Error adding column (maybe it already exists?): {e}")

