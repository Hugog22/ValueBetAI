from db.session import SessionLocal
from db.models import Match, Team
import os, json

db = SessionLocal()
squads_file = "data/world_cup_squads.json"
with open(squads_file, "r") as f:
    squads_data = json.load(f)
    wc_team_names = list(squads_data.keys())

teams = db.query(Team).filter(Team.name.in_(wc_team_names)).all()
wc_team_ids = [t.id for t in teams]

finished_wc = db.query(Match).filter(
    Match.status == "Finished",
    Match.home_team_id.in_(wc_team_ids)
).all()

print(f"Total finished WC matches: {len(finished_wc)}")
for m in finished_wc[:5]:
    print(f"Match {m.id} | Date: {m.date} | Home: {m.home_team.name} | Away: {m.away_team.name} | API ID: {m.api_football_id}")
