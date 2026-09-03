from sqlalchemy import create_engine, text
import os

engine = create_engine("postgresql+psycopg2://postgres.hwfjlxfbabcavigutimz:QuantStake2026Premium@aws-0-eu-west-1.pooler.supabase.com:6543/postgres")
with engine.connect() as conn:
    print("world_cup_team_stats count:", conn.execute(text("SELECT count(*) FROM world_cup_team_stats")).scalar())
    
    iran = conn.execute(text("SELECT id, name FROM teams WHERE name ILIKE '%Iran%'")).fetchall()
    print("Iran in teams:", iran)
    
    for row in iran:
        stats = conn.execute(text(f"SELECT id, matches_played FROM world_cup_team_stats WHERE team_id = {row[0]}")).fetchall()
        print(f"Stats for {row[1]}:", stats)
        
    nz = conn.execute(text("SELECT id, name FROM teams WHERE name ILIKE '%Zealand%'")).fetchall()
    print("NZ in teams:", nz)
    for row in nz:
        stats = conn.execute(text(f"SELECT id, matches_played FROM world_cup_team_stats WHERE team_id = {row[0]}")).fetchall()
        print(f"Stats for {row[1]}:", stats)
