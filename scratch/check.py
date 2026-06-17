import json, re

with open("backend/data/world_cup_squads.json") as f:
    squad_teams = set(json.load(f).keys())

with open("frontend/src/utils/translations.ts") as f:
    content = f.read()
    
# check each team in squad_teams if it exists in content
missing_names = []
missing_flags = []

for team in squad_teams:
    if f"'{team}':" not in content and f"{team}:" not in content and f'"{team}":' not in content:
        missing_names.append(team)

print("Total squad teams:", len(squad_teams))
print("Missing in translations.ts:", missing_names)
