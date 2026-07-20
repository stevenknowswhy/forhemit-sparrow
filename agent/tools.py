"""
Brave Search tool for the Sparrow agent.
Uses Brave Search API (free tier: 2,000 queries/month).
"""
import os
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from agent directory
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
BRAVE_BASE_URL = "https://api.search.brave.com/res/v1/web/search"


def search_brave(query: str, max_results: int = 10, country: str = "us", search_lang: str = "en") -> dict:
    """
    Search the web using Brave Search API.
    
    Args:
        query: Search query string
        max_results: Number of results to return (1-20)
        country: Country code for search results
        search_lang: Language code for search results
        
    Returns:
        Dict with 'results' list containing title, url, snippet for each result
    """
    if not BRAVE_API_KEY:
        logger.warning("BRAVE_SEARCH_API_KEY not set — returning stub results")
        return {
            "query": query,
            "results": [
                {
                    "title": f"Stub: {query}",
                    "url": "https://search.brave.com/search?q=" + requests.utils.quote(query),
                    "snippet": "Brave Search API key not configured. Set BRAVE_SEARCH_API_KEY in .env to enable real search."
                }
            ],
            "provider": "stub",
            "total_results": 1,
            "note": "Configure Brave Search API key for real results"
        }

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
        "freshness": "pw",  # past week for pricing freshness
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
            "provider": "brave",
            "total_results": len(formatted),
            "ranking_info": data.get("ranking", {}).get("response_count", 0),
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        logger.error(f"Brave Search HTTP error {status}: {e}")
        return {
            "query": query,
            "results": [],
            "provider": "error",
            "error": f"Brave Search API error: HTTP {status}",
        }
    except requests.exceptions.Timeout:
        logger.error("Brave Search request timed out")
        return {
            "query": query,
            "results": [],
            "provider": "error",
            "error": "Brave Search request timed out",
        }
    except Exception as e:
        logger.error(f"Brave Search unexpected error: {e}")
        return {
            "query": query,
            "results": [],
            "provider": "error",
            "error": str(e),
        }


def search_and_summarize(query: str, max_results: int = 5) -> str:
    """
    Search Brave and return a human-readable summary string.
    Used by the LangChain agent as the tool output.
    """
    data = search_brave(query, max_results=max_results)
    
    if data["provider"] == "stub":
        return (
            f"Search stub (Brave API key not configured).\n"
            f"Query: {query}\n"
            f"For real results, set BRAVE_SEARCH_API_KEY in agent/.env"
        )
    
    if data["provider"] == "error":
        return f"Search failed: {data.get('error', 'unknown error')}"
    
    lines = [f"Brave Search results for: \"{query}\" ({data['total_results']} results)\n"]
    for i, r in enumerate(data["results"], 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['url']}")
        lines.append(f"   {r['snippet']}")
        if r.get("extra_snippets"):
            for es in r["extra_snippets"]:
                lines.append(f"   ▸ {es}")
        lines.append("")
    
    return "\n".join(lines)
