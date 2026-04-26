"""
search_enrichment.py

Uses Brave Search API to enrich wine recommendations with a bottle
image and a buy/info link.

Two endpoints are used:
  - https://api.search.brave.com/res/v1/images/search  → bottle thumbnail
  - https://api.search.brave.com/res/v1/web/search     → buy/info link

Both are fired concurrently per wine to minimise latency.
This is utilizing Brave Search API's free tier, so this is more of a short term 
developmental/testing choice.

Setup:
  Add to your .env file:
    BRAVE_API_KEY=your_key_here
"""

import os
import asyncio
import httpx
from dataclasses import dataclass
from typing import Optional

### Global Variables

BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

BRAVE_IMAGE_URL = "https://api.search.brave.com/res/v1/images/search"
BRAVE_WEB_URL   = "https://api.search.brave.com/res/v1/web/search"

# Preferred retail domains: If a search result comes from one of these well known wine websites, they
# are preferred to results from other domains.
PREFERRED_DOMAINS = [
    "wine.com",
    "vivino.com",
    "totalwine.com",
    "klwines.com",
    "wine-searcher.com",
    "drizly.com",
]


@dataclass
class WineEnrichment:
    """
    Visual and link data to attach to a recommendation result card.
    All fields are Optional — enrichment always degrades gracefully.
    """
    wine_name: str

    # Image fields
    thumbnail_url: Optional[str] = None      
    image_source: Optional[str] = None 

    # Buy/info link fields
    buy_url: Optional[str] = None
    buy_source: Optional[str] = None


def _build_query(wine_name: str, winery: str, region: str) -> str:
    """
    Build the most accurate possible search name.
    """
    parts = [p.strip() for p in [winery, wine_name, region] if p and p.strip()]
    return " ".join(parts)


async def _brave_image_search(
    client: httpx.AsyncClient,
    query: str,
) -> list[dict]:
    """
    Search Brave's image index for result thumbnail to display on results page.
    Returns raw result list or [] on failure. 
    """
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "q": query,
        "count": 3,
        "search_lang": "en",
        "country": "us",
        "safesearch": "strict",
    }
    try:
        response = await client.get(
            BRAVE_IMAGE_URL,
            headers=headers,
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except httpx.HTTPStatusError as e:
        print(f"[brave:image] HTTP {e.response.status_code} — query: '{query}'")
        return []
    except Exception as e:
        print(f"[brave:image] error: {e}")
        return []


async def _brave_web_search(
    client: httpx.AsyncClient,
    query: str,
) -> list[dict]:
    """
    Search Brave's web index. Returns raw result list or [] on failure.
    """
    headers = {
        "X-Subscription-Token": BRAVE_API_KEY,
        "Accept": "application/json",
    }
    params = {
        "q": query,
        "count": 5, 
        "search_lang": "en",
        "country": "us",
    }
    try:
        response = await client.get(
            BRAVE_WEB_URL,
            headers=headers,
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("web", {}).get("results", [])
    except httpx.HTTPStatusError as e:
        print(f"[brave:web] HTTP {e.response.status_code} — query: '{query}'")
        return []
    except Exception as e:
        print(f"[brave:web] error: {e}")
        return []


def _pick_best_image(results: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """
    From a list of Brave image results, return (thumbnail_url, source_domain).
    Prefers results whose source domain looks like a wine retailer or winery.
    Falls back to the first result if nothing specific is found.
    """
    if not results:
        return None, None

    # Try to find an image from a known wine-related domain first
    for result in results:
        source = result.get("source", "")
        if any(d in source for d in PREFERRED_DOMAINS + ["winery", "wine", "cellar"]):
            thumb = result.get("thumbnail", {}).get("src")
            if thumb:
                return thumb, source

    # Fall back to first result regardless of source
    first = results[0]
    thumb = first.get("thumbnail", {}).get("src")
    source = first.get("source")
    return thumb, source


def _pick_best_link(results: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """
    From a list of Brave web results, return (url, source_domain).
    Prefers known retail domains over generic results.
    """
    if not results:
        return None, None

    # Scan top results for a preferred domain
    for result in results:
        hostname = result.get("meta_url", {}).get("hostname", "")
        if any(d in hostname for d in PREFERRED_DOMAINS):
            return result.get("url"), hostname

    # Fall back to the first result
    first = results[0]
    hostname = first.get("meta_url", {}).get("hostname", first.get("url", ""))
    return first.get("url"), hostname


async def enrich_wine(
    wine_name: str,
    winery: str = "",
    region: str = "",
    country: str = "",
) -> WineEnrichment:
    """
    Fetch a bottle thumbnail and buy link for a single wine.
    Fires both Brave searches concurrently (2 API calls total).
    Used in enriching result page for user query.
    """

    # Test for brave api key
    if not BRAVE_API_KEY:
        print("[brave] BRAVE_API_KEY not set — skipping enrichment")
        return WineEnrichment(wine_name=wine_name)

    # Set queries
    base_query  = _build_query(wine_name, winery, region)
    image_query = f"{base_query} wine bottle"
    web_query   = f"{base_query} wine buy"

    # Search concurrently for both thumbnail and buy link
    async with httpx.AsyncClient() as client:
        image_results, web_results = await asyncio.gather(
            _brave_image_search(client, image_query),
            _brave_web_search(client, web_query),
        )

    thumbnail_url, image_source = _pick_best_image(image_results)
    buy_url, buy_source         = _pick_best_link(web_results)

    return WineEnrichment(
        wine_name=wine_name,
        thumbnail_url=thumbnail_url,
        image_source=image_source,
        buy_url=buy_url,
        buy_source=buy_source,
    )


async def enrich_wines_batch(wines: list[dict]) -> list[WineEnrichment]:
    """
    Enrich a list of wines sequentially with a small delay between each
    to not violate brave's api call limit

    Each dict should have keys: wine_name, winery, region, country
    Returns results in the same order as input.
    """
    results = []
    for wine in wines:
        enrichment = await enrich_wine(
            wine_name=wine.get("wine_name", ""),
            winery=wine.get("winery", ""),
            region=wine.get("region", ""),
            country=wine.get("country", ""),
        )
        results.append(enrichment)
        await asyncio.sleep(0.3)
    return results