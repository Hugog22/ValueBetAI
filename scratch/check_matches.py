from sqlalchemy import create_engine, text
import os

engine = create_engine("postgresql+psycopg2://postgres.hwfjlxfbabcavigutimz:QuantStake2026Premium@aws-0-eu-west-1.pooler.supabase.com:6543/postgres")
with engine.connect() as conn:
    matches = conn.execute(text("SELECT id, home_team_id, away_team_id, status FROM matches WHERE home_team_id IN (73, 74) OR away_team_id IN (73, 74)")).fetchall()
    print("Matches with Iran (73) or NZ (74):")
    for m in matches:
        print(m)
        
    irans = conn.execute(text("SELECT id, name FROM teams WHERE name ILIKE '%Iran%'")).fetchall()
    print("All Irans:", irans)
