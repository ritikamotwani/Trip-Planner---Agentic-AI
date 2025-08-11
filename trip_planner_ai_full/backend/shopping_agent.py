from __future__ import annotations
import os, json, time, requests
from typing import List
from pydantic import BaseModel
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERP_ENDPOINT = "https://serpapi.com/search.json"
MODEL = os.getenv("SHOPPING_MODEL","gpt-4o-mini")
SITES = [
    # general
    "amazon.com", "walmart.com", "target.com", "bestbuy.com", "ebay.com",
    # outdoor/gear
    "rei.com", "backcountry.com", "moosejaw.com", "decathlon.com",
    "patagonia.com", "thenorthface.com", "columbia.com", "merrell.com",
    # apparel / misc
    "uniqlo.com", "urbanoutfitters.com"
]
client = OpenAI(api_key=OPENAI_API_KEY)

class ShopItem(BaseModel):
    item: str
    reason: str
    vendor: str | None = None
    est_price_usd: float | None = None
    link: str | None = None

def suggest_shopping(destinations: List[str], prefs: str, budget_slice: int) -> List[ShopItem]:
    base = _ai_names(destinations, prefs, budget_slice)
    print(base, "base", flush=True)
    return _enrich(base)

def _ai_names(destinations: List[str], prefs: str, budget_slice: int) -> List[ShopItem]:
    if not OPENAI_API_KEY:
        return [ShopItem(item="Power bank", reason="All-day navigation & photos")]
    system = (
        "You are a travel gear buyer. Recommend 3–6 PHYSICAL ITEMS a traveler should BUY BEFORE the trip. "
        "Do NOT list places to visit. Only return JSON exactly like: "
        "{\"items\":[{\"item\":\"...\",\"reason\":\"...\"}]}"
    )
    user_payload = {
        "destinations": destinations,
        "preferences": prefs,
        "budget_slice_usd": budget_slice
    }

    try:
        resp = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_payload)}
            ],
            temperature=0.7,
            max_output_tokens=8000
        )
        # Extract JSON string
        text = resp.output[0].content[0].text
        # Parse to dict
        obj = json.loads(text)
        items = obj.get("items", [])
        if not isinstance(items, list):
            raise ValueError("items is not a list")

        out: List[ShopItem] = []
        for x in items[:6]:
            out.append(ShopItem(
                item=(x.get("item", "")[:120]),
                reason=(x.get("reason", "")[:400])
            ))
        return out or _fallback_items(prefs)

    except Exception as e:
        print("Shopping _ai_names error:", repr(e))
        # Optional: print the raw text when debugging
        # print("RAW:", text if 'text' in locals() else None)
        return _fallback_items(prefs)

def _fallback_items(prefs: str) -> List[ShopItem]:
    base = [
        ShopItem(item="Universal travel adapter", reason="Works in most countries"),
        ShopItem(item="Lightweight rain jacket", reason="Weather-proofing for hikes/city walks"),
        ShopItem(item="Power bank", reason="All-day navigation & photos"),
    ]
    low = (prefs or "").lower()
    if "hike" in low: base.append(ShopItem(item="Trail shoes", reason="Grip on uneven terrain"))
    if "beach" in low: base.append(ShopItem(item="Quick-dry towel", reason="Beach & hostels"))
    return base[:6]

def _enrich(items: List[ShopItem]) -> List[ShopItem]:
    if not SERPAPI_API_KEY:
        return items

    from urllib.parse import quote_plus

    def first_link(p: dict, query: str) -> str | None:
        # Prefer a direct product/store link
        link = p.get("link") or p.get("product_link")
        if link:
            return link
        # Build a Google Shopping product URL if we have an id
        pid = p.get("product_id")
        if pid:
            return f"https://www.google.com/shopping/product/{pid}?hl=en&gl=us"
        # Last resort: a Google search deeplink for the item name
        return f"https://www.google.com/search?q={quote_plus(query)}"

    out: List[ShopItem] = []

    for it in items:
        try:
            res = requests.get(
                SERP_ENDPOINT,
                params={
                    "engine": "google_shopping",
                    "q": it.item,
                    "api_key": SERPAPI_API_KEY,
                    "gl": "us",
                    "hl": "en",
                },
                timeout=12,
            )
            products = (res.json().get("shopping_results") or [])
            best = None

            # 1) try to pick a result whose link matches preferred domains
            for p in products:
                link = p.get("link") or p.get("product_link") or ""
                if any(dom in link for dom in SITES):
                    best = p
                    break

            # 2) otherwise just take the first result
            if not best and products:
                best = products[0]

            if best:
                # link: prefer direct, else product_id URL, else Google search
                it.link = first_link(best, it.item)

                # vendor/source name
                it.vendor = best.get("source") or best.get("seller")

                # price: prefer numeric extracted_price, else parse "$12.34"
                if "extracted_price" in best and isinstance(best["extracted_price"], (int, float)):
                    it.est_price_usd = float(best["extracted_price"])
                else:
                    price_str = best.get("price")
                    if isinstance(price_str, str) and price_str.startswith("$"):
                        try:
                            it.est_price_usd = float(price_str.replace("$", "").replace(",", ""))
                        except Exception:
                            pass

        except Exception as e:
            # Don’t fail the request if SerpAPI hiccups
            print("SerpAPI enrich error:", repr(e))

        out.append(it)

    return out