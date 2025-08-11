from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import uuid4
import uvicorn
import openai
import os
import tiktoken
import httpx
from datetime import datetime
import asyncio
import re
from agents import Runner
import json

from flight_mcp import make_flights_agent, Flight, run_flights_agent
from hotels_mcp import make_hotels_agent, Stay, run_hotels_agent
from itinerary import make_itinerary_agent, llm_days, DayPlan
from shopping_agent import suggest_shopping

MODEL = "gpt-4o-mini"
SESSION_LIMIT = 10000

session_usage: dict[str, int] = {}
encoding = tiktoken.encoding_for_model(MODEL)
client = openai.OpenAI()
openai.OpenAI.api_key = os.getenv('OPENAI_API_KEY')

def estimate_tokens(messages: List[dict]) -> int:
    """Estimate tokens for the given list of chat messages."""
    tokens = 0
    for msg in messages:
        tokens += 4
        tokens += len(encoding.encode(msg.get("content", "")))
    tokens += 2
    return tokens

class ChatReq(BaseModel):
    session_id: str
    messages: List[dict]
    previous_response_id: Optional[str]

class ChatResp(BaseModel):
    reply: str
    response_id: str
    tokens_used: int
    tokens_remaining: int

class PlanReq(BaseModel):
    destinations: List[str] = Field(..., min_items=1)
    start_date: str
    end_date: str
    budget: int = Field(..., ge=100, le=100000)
    preferences: Optional[str] = ""
    stay_type: str = Field(..., pattern="^(hotel|airbnb|camping|glamping)$")
    origin: Optional[str] = "SFO"
    @field_validator("start_date","end_date")
    @classmethod
    def _iso(cls, v: str) -> str: datetime.fromisoformat(v); return v

class PlanResp(BaseModel):
    destination: List[str]
    start_date: str
    end_date: str
    budget: int
    preferences: str
    stay_type: str
    day_plans: List[DayPlan]
    flights: List[Flight]
    stays: List[Stay]
    shopping: List[dict]  # from ShopItem (simple for now)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

async def run_itinerary_agent(itinerary_agent, destinations: List[str], start: str, end: str, prefs: str) -> List[DayPlan]:
    prompt = (
        'Return ONLY JSON: {"days":[{"day":int,"date":"YYYY-MM-DD","title":str,'
        '"summary":str,"activities":[str]}]}.\n'
        f"destinations={destinations}\nstart_date={start}\nend_date={end}\n"
        f"preferences={prefs or ''}\nlimit_activities_per_day=5"
    )

    run = await Runner.run(itinerary_agent, prompt)

    # 0) normalize `run` to something we can parse
    out = None
    if isinstance(run, tuple) and run:                      # (result, state) pattern
        run = run[0]
    out = getattr(run, "final_output", None) or getattr(run, "output_text", None) or run

    # 1) dict -> read directly
    if isinstance(out, dict):
        days = out.get("days") or out.get("day_plans") or []
        return [DayPlan(**d) for d in days]

    # 2) string -> parse JSON (direct or first {...} block)
    if isinstance(out, str):
        s = out.strip()
        if s.startswith("{"):
            try:
                obj = json.loads(s)
                days = obj.get("days") or obj.get("day_plans") or []
                return [DayPlan(**d) for d in days]
            except Exception:
                pass
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            try:
                obj = json.loads(m.group(0))
                days = obj.get("days") or obj.get("day_plans") or []
                return [DayPlan(**d) for d in days]
            except Exception:
                pass

    # 3) object with dict-like attr
    if hasattr(out, "__dict__"):
        d = out.__dict__
        if "days" in d or "day_plans" in d:
            days = d.get("days") or d.get("day_plans") or []
            return [DayPlan(**d) for d in days]

    # 4) nothing usable -> empty; caller can fallback to llm_days
    return []

@app.middleware("http")
async def add_session_cookie(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid4())
    response: Response = await call_next(request)
    response.set_cookie("session_id", session_id, max_age=3600)
    return response

@app.get("/")
def read_root():
    return {"message": "Trip Planner API is running"}

def parse_preferences(prefs: str) -> List[str]:
    if not prefs: return []
    tokens = [t.strip().lower() for t in prefs.replace(",", " ").split() if t.strip()]
    seen, out = set(), []
    for t in tokens:
        if t not in seen:
            seen.add(t); out.append(t)
    print(out)
    return out

@app.post("/plan", response_model=PlanResp)
async def plan_trip(req: PlanReq):
    start = datetime.fromisoformat(req.start_date)
    end   = datetime.fromisoformat(req.end_date)
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be on/before end_date")

    # Budget split (simple heuristic)
    flights_budget = int(req.budget * 0.4)
    stays_budget   = int(req.budget * 0.4)
    misc_budget    = req.budget - flights_budget - stays_budget

    # Build agents (MCP URLs optional; your factories can attach tools if set)
    flights_agent = await make_flights_agent(os.getenv("FLIGHTS_MCP_URL"))
    hotels_agent  = await make_hotels_agent(os.getenv("HOTELS_MCP_URL"))
    itinerary_agent = make_itinerary_agent(flights_agent, hotels_agent)

    # 1) Itinerary with itinerary agent (single source of truth for day_plans)
    try:
        day_plans = await run_itinerary_agent(
            itinerary_agent,
            req.destinations,
            req.start_date,
            req.end_date,
            req.preferences or ""
        )
        print(day_plans)
        if not day_plans:
            raise ValueError("empty itinerary")
    except Exception as e:
        # Optional: fallback to a tiny deterministic stub or raise
        raise HTTPException(status_code=502, detail=f"itinerary agent failed: {e}")

    # 2) Flights with flights agent (returns real links if tools wired)
    try:
        flights = await run_flights_agent(
            flights_agent,
            origin=req.origin or "SFO",
            destinations=req.destinations,
            start=req.start_date,
            end=req.end_date,
            budget_slice=flights_budget
        )
        print(flights, "flights")
    except Exception as e:
        flights = []  # or raise

    # 3) Stays with hotels agent
    try:
        nights = max((end - start).days, 1)
        stays = await run_hotels_agent(
            hotels_agent,
            destinations=req.destinations,
            stay_type=req.stay_type,
            nights=nights,
            budget_slice=stays_budget
        )
        print(stays)
    except Exception as e:
        stays = []  # or raise

    # 4) Shopping (LLM propose → verified links inside your shopping_agent)
    shopping_items = suggest_shopping(req.destinations, req.preferences or "", misc_budget)

    return PlanResp(
        destination=req.destinations,
        start_date=req.start_date,
        end_date=req.end_date,
        budget=req.budget,
        preferences=req.preferences or "",
        stay_type=req.stay_type,
        day_plans=day_plans,
        flights=flights,
        stays=stays,
        shopping=[s.model_dump() for s in shopping_items]
    )

@app.get("/locations")
async def autocomplete_locations(
    query: str = Query(..., min_length=2, description="Search text for cities or countries"),
    limit: int = Query(5, ge=1, le=10, description="Max number of suggestions"),
):
    """
    Return a list of place names matching the query string.
    Uses OpenStreetMap Nominatim for simple geocoding.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 0,
        "limit": limit,
    }
    headers = {
        "User-Agent": "WanderlustApp/1.0 (youremail@example.com)",  # identify your app
        "Referer": "http://localhost:5173"
    }
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

    # Extract display names
    suggestions = [item["display_name"] for item in data]
    return {"locations": suggestions}

@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq, request: Request):
    session = req.session_id
    used = session_usage.get(session, 0)

    prompt_tokens = estimate_tokens(req.messages)
    if used + prompt_tokens > SESSION_LIMIT:
        return ChatResp(
            reply="Session token limit reached. Please refresh to start a new session.",
            response_id="",
            tokens_used=used,
            tokens_remaining=0
        )
    resp = client.responses.create(
        model=MODEL,
        input=req.messages,
        previous_response_id=req.previous_response_id,
        max_output_tokens = 1000,
    )
    print(resp)
    output_msg = resp.output[0]
    print(output_msg)
    reply_text = "".join(chunk.text for chunk in output_msg.content)
    tokens_used = resp.usage.total_tokens 

    session_usage[session] = used + tokens_used

    return ChatResp(
        reply=reply_text,
        response_id=resp.id,
        tokens_used=session_usage[session],
        tokens_remaining=SESSION_LIMIT - session_usage[session]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)