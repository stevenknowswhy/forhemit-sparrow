"""
Search provider abstraction for the Sparrow agent.
Supports Serper.dev, Walmart, Best Buy, Tavily, and Brave Search as backends.

Backend priority:
  1. Serper    (2,500 free/month, Google Shopping prices & ratings)
  2. Walmart   (free, Marketplace Commerce API — structured prices, stock status)
  3. Best Buy  (free, public API — prices, ratings, freeShipping flag, availability)
  4. Tavily    (1,000 free/month, AI-native search with full page content)
  5. Brave     (2,000 free/month, general web results)
  6. Stub      (built-in demo data when no API keys are set)
"""
from __future__ import annotations
import os
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_BASE_URL = "https://google.serper.dev/search"
SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
BRAVE_BASE_URL = "https://api.search.brave.com/res/v1/web/search"

WALMART_CLIENT_ID = os.getenv("WALMART_CLIENT_ID")
WALMART_CLIENT_SECRET = os.getenv("WALMART_CLIENT_SECRET")
WALMART_AUTH_URL = "https://marketplace.walmartapis.com/v3/token"
WALMART_SEARCH_URL = "https://marketplace.walmartapis.com/v3/items/search"

BESTBUY_API_KEY = os.getenv("BESTBUY_API_KEY")
BESTBUY_BASE_URL = "https://api.bestbuy.com/v1"


def search(query: str, max_results: int = 10) -> dict:
    if SERPER_API_KEY:
        result = search_serper(query, max_results=max_results)
        if result.get("total_results", 0) > 0:
            return result
        logger.info("Serper returned no results")

    if WALMART_CLIENT_ID and WALMART_CLIENT_SECRET:
        result = search_walmart(query, max_results=max_results)
        if result.get("total_results", 0) > 0:
            logger.info("Walmart API returned %d results", result["total_results"])
            return result
        logger.info("Walmart returned no results")

    if BESTBUY_API_KEY:
        result = search_bestbuy(query, max_results=max_results)
        if result.get("total_results", 0) > 0:
            logger.info("Best Buy API returned %d results", result["total_results"])
            return result
        logger.info("Best Buy returned no results")

    if TAVILY_API_KEY:
        result = search_tavily(query, max_results=max_results)
        if result.get("total_results", 0) > 0:
            return result
        logger.info("Tavily returned no results")

    if BRAVE_API_KEY:
        result = search_brave(query, max_results=max_results)
        if result.get("total_results", 0) > 0:
            return result
        logger.info("Brave returned no results")

    return search_stub(query)


def search_stub(query: str) -> dict:
    return {
        "query": query,
        "results": [
            {
                "title": f"Stub: {query}",
                "url": "https://search.brave.com/search?q=" + requests.utils.quote(query),
                "snippet": "No search API key configured. Set SERPER_API_KEY or BRAVE_SEARCH_API_KEY in .env to enable real search.",
                "extra_snippets": [],
            }
        ],
        "provider": "stub",
        "total_results": 1,
        "note": "Configure an API key for real results",
    }


def _parse_price(price_raw: str) -> float | None:
    if not price_raw:
        return None
    cleaned = price_raw.replace("$", "").replace("€", "").replace("£", "").replace(",", "")
    try:
        return float(cleaned) if cleaned.replace(".", "").isdigit() else None
    except (ValueError, TypeError):
        return None


def _serper_get_organic(query: str, headers: dict, max_results: int = 10) -> list[dict]:
    try:
        payload = {"q": query, "num": min(max_results, 10)}
        resp = requests.post(SERPER_BASE_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        organic = []
        for r in data.get("organic", [])[:max_results]:
            organic.append({
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
                "rating": r.get("rating"),
                "review_count": r.get("ratingCount", 0),
                "extra_snippets": [],
            })
        return organic
    except requests.exceptions.RequestException as e:
        logger.error(f"Serper.dev search endpoint failed: {e}")
        return []


def search_serper(query: str, max_results: int = 10) -> dict:
    if not SERPER_API_KEY:
        return {"query": query, "results": [], "shopping": [], "provider": "unconfigured"}

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    shopping: list[dict] = []
    organic: list[dict] = []

    try:
        payload = {"q": query, "num": min(max_results, 20)}
        shopping_resp = requests.post(SERPER_SHOPPING_URL, headers=headers, json=payload, timeout=15)
        shopping_resp.raise_for_status()
        shopping_data = shopping_resp.json()
        items = shopping_data.get("shopping", [])[:max_results]

        for s in items:
            shopping.append({
                "title": s.get("title", ""),
                "url": s.get("link", ""),
                "price": s.get("price", ""),
                "price_value": _parse_price(s.get("price", "")),
                "rating": s.get("rating"),
                "review_count": s.get("ratingCount", s.get("reviewCount", 0)),
                "source": s.get("source", ""),
                "image_url": s.get("imageUrl", ""),
            })

        organic = _serper_get_organic(query, headers, max_results)

    except requests.exceptions.RequestException as e:
        logger.error(f"Serper.dev shopping endpoint failed: {e}")
        organic = _serper_get_organic(query, headers, max_results)

    return {
        "query": query,
        "results": organic,
        "shopping": shopping,
        "provider": "serper",
        "total_results": len(shopping) or len(organic),
    }


def search_tavily(query: str, max_results: int = 10) -> dict:
    if not TAVILY_API_KEY:
        return {"query": query, "results": [], "provider": "unconfigured", "total_results": 0}

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": min(max_results, 20),
        "include_answer": False,
        "include_raw_content": False,
    }

    try:
        resp = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0),
            })

        return {
            "query": query,
            "results": results,
            "provider": "tavily",
            "total_results": len(results),
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Tavily search request failed: {e}")
        return {"query": query, "results": [], "provider": "error", "error": str(e), "total_results": 0}


def extract_tavily(urls: list[str]) -> list[dict]:
    if not TAVILY_API_KEY or not urls:
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "urls": urls[:5],
        "include_images": False,
    }

    try:
        resp = requests.post(TAVILY_EXTRACT_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Tavily extract request failed: {e}")
        return []


def search_brave(query: str, max_results: int = 10, country: str = "us", search_lang: str = "en") -> dict:
    if not BRAVE_API_KEY:
        return search_stub(query)

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }

    params = {
        "q": query,
        "count": min(max_results, 20),
        "country": country,
        "search_lang": search_lang,
    }

    try:
        resp = requests.get(BRAVE_BASE_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        web_results = data.get("web", {}).get("results", [])

        formatted = []
        for r in web_results[:max_results]:
            formatted.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("description", ""),
                "extra_snippets": r.get("extra_snippets", []),
            })

        return {
            "query": query,
            "results": formatted,
            "shopping": [],
            "provider": "brave",
            "total_results": len(formatted),
            "ranking_info": data.get("ranking", {}).get("response_count", 0),
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        logger.error(f"Brave Search HTTP error {status}: {e}")
        return {"query": query, "results": [], "shopping": [], "provider": "error", "error": f"Brave Search API error: HTTP {status}"}
    except requests.exceptions.Timeout:
        logger.error("Brave Search request timed out")
        return {"query": query, "results": [], "shopping": [], "provider": "error", "error": "Brave Search request timed out"}
    except Exception as e:
        logger.error(f"Brave Search unexpected error: {e}")
        return {"query": query, "results": [], "shopping": [], "provider": "error", "error": str(e)}


def search_walmart(query: str, max_results: int = 10) -> dict:
    if not WALMART_CLIENT_ID or not WALMART_CLIENT_SECRET:
        return {"query": query, "results": [], "shopping": [], "provider": "unconfigured", "total_results": 0}

    try:
        token_resp = requests.post(
            WALMART_AUTH_URL,
            auth=(WALMART_CLIENT_ID, WALMART_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return {"query": query, "results": [], "shopping": [], "provider": "error", "total_results": 0}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "WM_SVC.NAME": "Walmart Marketplace",
            "WM_QOS.CORRELATION_ID": query.replace(" ", "_")[:64],
        }
        params = {"search": query, "limit": min(max_results, 20)}
        resp = requests.get(WALMART_SEARCH_URL, headers=headers, params=params, timeout=15)
        if resp.status_code == 401:
            return {"query": query, "results": [], "shopping": [], "provider": "unconfigured", "total_results": 0}
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])[:max_results]
        shopping = []
        for item in items:
            price_info = item.get("price", [{}])
            price_val = price_info[0].get("value") if isinstance(price_info, list) and price_info else None
            price_str = f"${price_val}" if price_val else ""
            shopping.append({
                "title": item.get("productName", ""),
                "url": item.get("productUrl", ""),
                "price": price_str,
                "price_value": float(price_val) if price_val else None,
                "rating": float(item["customerRating"]) if item.get("customerRating") else None,
                "review_count": int(item["customerReviews"]) if item.get("customerReviews") else 0,
                "source": "Walmart",
                "image_url": item.get("imageUrl", ""),
                "free_shipping": None,
                "shipping_cost": None,
                "in_stock": item.get("stock", "") == "IN_STOCK",
            })

        return {
            "query": query,
            "results": [],
            "shopping": shopping,
            "provider": "walmart",
            "total_results": len(shopping),
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Walmart API request failed: {e}")
        return {"query": query, "results": [], "shopping": [], "provider": "error", "error": str(e), "total_results": 0}


def search_bestbuy(query: str, max_results: int = 10) -> dict:
    if not BESTBUY_API_KEY:
        return {"query": query, "results": [], "shopping": [], "provider": "unconfigured", "total_results": 0}

    try:
        url = (f"{BESTBUY_BASE_URL}/products(search={requests.utils.quote(query)})"
               f"?format=json&show=sku,name,salePrice,regularPrice,customerReviewAverage,"
               f"customerReviewCount,freeShipping,description,manufacturer,url,"
               f"inStoreAvailability,onlineAvailability"
               f"&apiKey={BESTBUY_API_KEY}&pageSize={min(max_results, 20)}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        products = data.get("products", [])[:max_results]
        shopping = []
        for p in products:
            price_val = p.get("salePrice") or p.get("regularPrice")
            price_str = f"${price_val}" if price_val else ""
            shopping.append({
                "title": p.get("name", ""),
                "url": p.get("url", ""),
                "price": price_str,
                "price_value": float(price_val) if price_val else None,
                "rating": float(p["customerReviewAverage"]) if p.get("customerReviewAverage") else None,
                "review_count": int(p["customerReviewCount"]) if p.get("customerReviewCount") else 0,
                "source": "Best Buy",
                "image_url": "",
                "free_shipping": bool(p.get("freeShipping", False)),
                "shipping_cost": 0.0 if p.get("freeShipping", False) else None,
                "in_stock": p.get("onlineAvailability", False) or p.get("inStoreAvailability", False),
            })

        return {
            "query": query,
            "results": [],
            "shopping": shopping,
            "provider": "bestbuy",
            "total_results": data.get("total", len(shopping)),
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Best Buy API request failed: {e}")
        return {"query": query, "results": [], "shopping": [], "provider": "error", "error": str(e), "total_results": 0}


def fetch_page_html(url: str, timeout: int = 8) -> str | None:
    """Fetch a product page and return its HTML, or None on failure."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            logger.debug("fetch_page_html: non-HTML content type %s for %s", ctype, url)
            return None
        return resp.text
    except requests.exceptions.RequestException:
        logger.debug("fetch_page_html: failed to fetch %s", url)
        return None


def search_and_summarize(query: str, max_results: int = 5) -> str:
    data = search(query, max_results=max_results)
    provider = data.get("provider", "unknown")

    if data.get("error"):
        return f"Search failed ({provider}): {data['error']}"

    total = data.get("total_results", 0)
    if total == 0:
        return f"No results from {provider} for: {query}"

    lines = [f"Search results for: \"{query}\" ({total} results, backend: {provider})\n"]

    if data.get("shopping"):
        lines.append("--- Shopping Results ---")
        for i, s in enumerate(data["shopping"][:5], 1):
            parts = [f"{i}. {s['title']}"]
            if s.get("price"):
                parts.append(f"   Price: {s['price']}")
            if s.get("rating"):
                parts.append(f"   Rating: {s['rating']}/5 ({s.get('review_count', 0)} reviews)")
            if s.get("source"):
                parts.append(f"   Source: {s['source']}")
            parts.append(f"   {s.get('url', '')}")
            lines.append("\n".join(parts))
        lines.append("")

    lines.append("--- Web Results ---")
    for i, r in enumerate(data["results"][:max_results], 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        snippet = r.get("content") or r.get("snippet", "")
        lines.append(f"   {snippet[:200]}")
        lines.append("")

    return "\n".join(lines)
