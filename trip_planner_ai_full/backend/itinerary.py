from __future__ import annotations
import os, json, requests
from pydantic import BaseModel
from datetime import datetime
from typing import List
from agents import Agent, Runner, handoff, input_guardrail, GuardrailFunctionOutput, RunContextWrapper

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("ITINERARY_MODEL", "gpt-4o-mini")

class DayPlan(BaseModel):
    day: int
    date: str
    title: str
    summary: str
    activities: List[str]

class ItineraryOutput(BaseModel):
    day_plans: List[DayPlan]
    notes: str

# guardrail to ensure it's travel-related
class TravelCheck(BaseModel):
    reasoning: str
    is_travel_related: bool

travel_check_agent = Agent(
    name="Travel topic checker",
    instructions=(
        "Decide if the user input is travel-related. "
        "Return JSON: {reasoning, is_travel_related}."
    ),
    output_type=TravelCheck,
    model=MODEL
)

@input_guardrail
async def travel_topic_guardrail(ctx: RunContextWrapper, agent: Agent, user_input: str) -> GuardrailFunctionOutput:
    result = await Runner.run(travel_check_agent, f"User input: {user_input}", context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not bool(result.final_output.is_travel_related),
    )

def make_itinerary_agent(flights_agent: Agent, hotels_agent: Agent) -> Agent:
    return Agent(
        name="Itinerary Planner",
        model=MODEL,
        instructions=(
            "You are a travel planner. Create a day-by-day detailed itinerary between start_date and end_date. It should be a detailed itinerary with all the activities and details. Name the activities and include the time of the day. Limit the number of activities per day to 5."
            "When you need flight info, HANDOFF to Flight Booker. "
            "When you need hotel info, HANDOFF to Hotel Finder. "
            "Then synthesize into JSON: { day_plans: [{day,date,title,summary,activities[]}], notes }."
        ),
        input_guardrails=[travel_topic_guardrail],
        handoffs=[handoff(flights_agent), handoff(hotels_agent)],
        output_type=ItineraryOutput
    )

def llm_days(destinations: List[str], start: datetime, end: datetime, prefs: str) -> List[DayPlan]:
    """Fallback: directly produce day plans via Responses API if needed."""
    payload = {
        "model": MODEL,
        "input":[
            {"role":"system","content":"Return ONLY JSON with {\"days\":[{day,date,title,summary,activities[]}]}."},
            {"role":"user","content": json.dumps({
                "destinations": destinations,
                "date_range":[start.date().isoformat(), end.date().isoformat()],
                "preferences": prefs, "max_per_day": 5
            })}
        ],
        "response_format":{"type":"json_object"}
    }
    r = requests.post("https://api.openai.com/v1/responses",
                      headers={"Authorization": f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
                      json=payload, timeout=30)
    r.raise_for_status()
    text = r.json().get("output_text") or r.json()["output"][0]["content"][0]["text"]
    obj = json.loads(text or "{}")
    return [DayPlan(**d) for d in obj.get("days", [])]
