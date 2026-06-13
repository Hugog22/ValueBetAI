import httpx
from core.config import settings

def test_api():
    url = "https://api.football-data.org/v4/competitions/WC/matches"
    headers = {"X-Auth-Token": settings.FOOTBALL_DATA_API_KEY}
    
    with httpx.Client() as client:
        resp = client.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            print(resp.text)
            return
            
        data = resp.json()
        matches = data.get("matches", [])
        
        for m in matches:
            home = m.get("homeTeam", {}).get("name", "")
            away = m.get("awayTeam", {}).get("name", "")
            
            # Check for Mexico vs South Africa
            if "Mexico" in home or "Mexico" in away or "South Africa" in home or "South Africa" in away:
                print(f"Match ID: {m.get('id')}")
                print(f"Teams: {home} vs {away}")
                print(f"Date: {m.get('utcDate')}")
                print(f"Status: {m.get('status')}")
                print(f"Score: {m.get('score')}")
                print("-" * 40)

if __name__ == "__main__":
    test_api()
