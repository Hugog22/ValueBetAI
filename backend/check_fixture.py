import httpx
from core.config import settings
resp = httpx.get(
    "https://v3.football.api-sports.io/fixtures",
    headers={"x-apisports-key": settings.API_SPORTS_KEY},
    params={"id": 29451}
)
print(resp.json())
