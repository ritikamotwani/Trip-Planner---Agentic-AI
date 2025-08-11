# flight_mcp.py
from __future__ import annotations
import os, json, time, requests
from typing import List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from agents import Agent, Runner
import asyncio

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERP_ENDPOINT = "https://serpapi.com/search.json"
FLIGHTS_MODEL = os.getenv("FLIGHTS_MODEL", "gpt-4o-mini")

class Flight(BaseModel):
    airline: str
    from_: str = Field(..., alias="from")
    to: str
    depart: str
    arrive: Optional[str] = None
    price: int
    link: Optional[str] = None
    class Config: populate_by_name = True

async def make_flights_agent(mcp_url: Optional[str]) -> Agent:
    servers = []
    return Agent(
        name="Flight Booker",
        model=FLIGHTS_MODEL,
        instructions=(
            "Find ROUND-TRIP flights. If an MCP tool `search_flights` is available, use it. "
            'Return ONLY JSON: {"legs":[{"airline":str,"from":str,"to":str,"depart":iso,"arrive":iso?,"price":int,"link":str?}]}. '
            "Prefer Google Flights deeplinks or airline booking links."
        )
    )

async def run_flights_agent(
    agent, origin: str, destinations: List[str],
    start: datetime, end: datetime, budget_slice: int
) -> List[Flight]:
    out: List[Flight] = []
    print(destinations, "destinations", flush=True)

    # Guard: agent must exist
    if not agent:
        print("Flights agent is None → using SerpAPI fallback for all destinations", flush=True)
        for dest in destinations:
            out.extend(_serp_roundtrip(origin, dest, start, end))
        return out

    for dest in destinations:
        print(origin, "origin", flush=True)

        prompt = (
            'Return ONLY JSON: {"legs":[{"airline":str,"from":str,"to":str,'
            '"depart":"YYYY-MM-DDTHH:MM:SS","arrive":"YYYY-MM-DDTHH:MM:SS",'
            '"price":int,"link":str}]}.\n'
            f"round_trip=true\norigin={origin}\ndestination={dest}\n"
            f"depart_date={start.date().isoformat()}\nreturn_date={end.date().isoformat()}\n"
            f"currency=USD\nprice_hint={budget_slice}\n"
            "Prefer reputable links (Google Flights deeplink or airline)."
        )
        print(prompt, "prompt", flush=True)

        # Try agent with timeout — if it hangs, we fallback
        try:
            res = await asyncio.wait_for(Runner.run(agent, prompt), timeout=25)
        except asyncio.TimeoutError:
            print(f"[flights] Runner timeout for {origin}->{dest} → fallback", flush=True)
            out.extend(_serp_roundtrip(origin, dest, start, end))
            time.sleep(0.2)
            continue
        except Exception as e:
            print(f"[flights] Runner error for {origin}->{dest}: {repr(e)} → fallback", flush=True)
            out.extend(_serp_roundtrip(origin, dest, start, end))
            time.sleep(0.2)
            continue

        # Normalize result
        data = getattr(res, "final_output", None)
        if data is None:
            data = getattr(res, "output_text", None) or res

        # Parse shapes: dict or string JSON
        try:
            if isinstance(data, str):
                data = json.loads(data or "{}")
            elif hasattr(data, "model_dump"):
                data = data.model_dump()
            elif hasattr(data, "__dict__") and not isinstance(data, dict):
                data = data.__dict__
        except Exception as pe:
            print(f"[flights] parse error → {repr(pe)}; raw: {type(data)} {data}", flush=True)
            data = {}

        legs = (data or {}).get("legs", [])
        if not isinstance(legs, list):
            legs = []

        # Coerce to Flight list
        try:
            parsed = [Flight(**leg) for leg in legs]
        except Exception as ve:
            print(f"[flights] schema error → {repr(ve)}; legs: {legs}", flush=True)
            parsed = []

        if parsed:
            out.extend(parsed)
            print(f"[flights] agent returned {len(parsed)} legs for {dest}", flush=True)
            time.sleep(0.2)
        else:
            print(f"[flights] empty/no legs for {dest} → fallback", flush=True)
            out.extend(_serp_roundtrip(origin, dest, start, end))
            time.sleep(0.2)

    print(out, "out", flush=True)
    return out

def _serp_roundtrip(origin: str, dest: str, start: datetime, end: datetime) -> List[Flight]:
    if not SERPAPI_API_KEY:
        # bare minimum deeplinks if no API key
        gf = lambda a,b,d: f"https://www.google.com/travel/flights?q=Flights%20from%20{a}%20to%20{b}%20on%20{d}"
        return [
            Flight(airline="Multiple", **{"from": origin}, to=dest, depart=f"{start.date()}T09:00:00", price=0, link=gf(origin, dest, start.date())),
            Flight(airline="Multiple", **{"from": dest}, to=origin, depart=f"{end.date()}T18:00:00", price=0, link=gf(dest, origin, end.date())),
        ]
    r = requests.get(SERP_ENDPOINT, params={
        "engine":"google_flights","api_key":SERPAPI_API_KEY,"hl":"en","gl":"us",
        "departure_id":origin,"arrival_id":dest,
        "outbound_date":start.date().isoformat(),"return_date":end.date().isoformat(),"currency":"USD"
    }, timeout=15)
    r.raise_for_status()
    data = r.json()

    def price_to_int(s):
        if isinstance(s,str) and s.strip().startswith("$"):
            try: return int(float(s.replace("$","").replace(",","")))
            except: return None
        return None

    legs: List[Flight] = []
    best = (data or {}).get("best_flights") or []
    if best:
        b = best[0]; price = price_to_int(b.get("price")) or 0; link = b.get("link")
        segs = b.get("flights", [])
        if segs:
            # first segment ≈ outbound, last ≈ inbound
            first, last = segs[0], segs[-1]
            legs.append(Flight(
                airline=first.get("airline","Multiple"),
                **{"from": first.get("departure_airport",{}).get("code") or origin},
                to=first.get("arrival_airport",{}).get("code") or dest,
                depart=first.get("departure_time") or f"{start.date()}T09:00:00",
                price=price, link=link
            ))
            legs.append(Flight(
                airline=last.get("airline","Multiple"),
                **{"from": last.get("departure_airport",{}).get("code") or dest},
                to=last.get("arrival_airport",{}).get("code") or origin,
                depart=last.get("departure_time") or f"{end.date()}T18:00:00",
                price=price, link=link
            ))
    if not legs:
        gf = lambda a,b,d: f"https://www.google.com/travel/flights?q=Flights%20from%20{a}%20to%20{b}%20on%20{d}"
        legs = [
            Flight(airline="Multiple", **{"from": origin}, to=dest, depart=f"{start.date()}T09:00:00", price=0, link=gf(origin, dest, start.date())),
            Flight(airline="Multiple", **{"from": dest}, to=origin, depart=f"{end.date()}T18:00:00", price=0, link=gf(dest, origin, end.date())),
        ]
    return legs
