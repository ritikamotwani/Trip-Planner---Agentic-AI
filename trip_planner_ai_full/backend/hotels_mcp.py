# hotels_mcp.py
from __future__ import annotations
import os, json, time, requests
from typing import List, Optional
from pydantic import BaseModel
from agents import Agent, Runner

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERP_ENDPOINT = "https://serpapi.com/search.json"
HOTELS_MODEL = os.getenv("HOTELS_MODEL", "gpt-4o-mini")

class Stay(BaseModel):
    name: str
    type: str
    location: str
    price_per_night: int
    nights: int
    link: Optional[str] = None

async def make_hotels_agent(mcp_url: Optional[str]) -> Agent:
    servers = []
    return Agent(
        name="Hotel Finder",
        model=HOTELS_MODEL,
        instructions=(
            "Find accommodations by city/date/type. If MCP tool `search_hotels` exists, use it. "
            'Return ONLY JSON: {"stays":[{"name":str,"type":"hotel|airbnb|camping|glamping","location":str,'
            '"price_per_night":int,"nights":int,"link":str?}]}. Prefer reputable links.'
        )
    )

async def run_hotels_agent(agent: Agent, destinations: List[str], stay_type: str, nights: int, budget_slice: int) -> List[Stay]:
    prompt = (
        'Return ONLY JSON {"stays":[{"name":str,"type":"hotel|airbnb|camping|glamping",'
        '"location":str,"price_per_night":int,"nights":int,"link":str?}]}\n'
        f"destinations={destinations}\nstay_type={stay_type}\nnights={nights}\n"
        f"budget_slice_usd={budget_slice}\ncurrency=USD\nPrefer Booking/Airbnb or official site links."
    )
    try:
        res = await Runner.run(agent, prompt)
        data = res.final_output
        data = data if isinstance(data, dict) else json.loads(data or "{}")
        stays = [Stay(**s) for s in data.get("stays", [])]
        if stays:
            return stays
    except Exception:
        pass
    # Fallback: SerpAPI Google results per destination (gets a reasonable link)
    return _serp_hotels(destinations, stay_type, nights, budget_slice)

def _serp_hotels(destinations: List[str], stay_type: str, nights: int, budget_slice: int) -> List[Stay]:
    out: List[Stay] = []
    per_night = max(40, min(400, budget_slice // max(1, nights * max(1, len(destinations)))))
    if not SERPAPI_API_KEY:
        for d in destinations:
            out.append(Stay(name=f"{stay_type.title()} in {d}", type=stay_type, location=d, price_per_night=per_night, nights=max(1, nights//max(1,len(destinations))), link=None))
        return out
    for d in destinations:
        try:
            q = f"{stay_type} in {d}"
            r = requests.get(SERP_ENDPOINT, params={"engine":"google","q":q,"api_key":SERPAPI_API_KEY,"gl":"us","hl":"en"}, timeout=12)
            link = (r.json().get("organic_results") or [{}])[0].get("link")
        except Exception:
            link = None
        out.append(Stay(name=f"{stay_type.title()} in {d}", type=stay_type, location=d,
                        price_per_night=per_night, nights=max(1, nights//max(1,len(destinations))), link=link))
        time.sleep(0.15)
    return out
