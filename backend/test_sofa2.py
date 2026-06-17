import httpx
import json

url = "https://sofascore6.p.rapidapi.com/api/sofascore/v1/search/matches"
headers = {
    "x-rapidapi-key": "960fa6f9f9msh1bf29c336215037p1095d5jsn2aaa4e9c7955",
    "x-rapidapi-host": "sofascore6.p.rapidapi.com"
}
resp = httpx.get(url, params={"q": "Cape Verde"}, headers=headers)
print(json.dumps(resp.json(), indent=2))
