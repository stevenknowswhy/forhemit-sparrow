"""
Store access layer — tries multiple methods to fetch product pages,
logs what works per store, and generates per-store skills.

Method priority (fastest first):
  1. Direct HTTP (requests) — works for most independent stores
  2. Crawl4AI — LLM-friendly clean extraction
  3. Playwright — full browser render, highest success rate
  4. Tavily extract — fallback API-based extraction
"""
from __future__ import annotations
import os
import re
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_STORE_DIR = Path(__file__).parent / "store_access"
_LOG_DIR = _STORE_DIR / "logs"
_SKILL_DIR = _STORE_DIR / "skills"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_SKILL_DIR.mkdir(parents=True, exist_ok=True)


# ── Store / domain helpers ──────────────────────────────────────────

def extract_store_name(url: str) -> str:
    domain = extract_domain(url)
    known = {
        "bestbuy": "Best Buy", "walmart": "Walmart",
        "amazon": "Amazon", "newegg": "Newegg",
        "staples": "Staples", "officedepot": "Office Depot",
        "hp.com": "HP", "dell.com": "Dell", "lenovo": "Lenovo",
        "target": "Target", "lowes": "Lowe's",
        "homedepot": "Home Depot", "brother": "Brother",
        "cdw": "CDW", "bhphotovideo": "B&H Photo",
        "inkgenie": "InkGenie", "inkjets": "InkJets",
        "google.com": "Google",
    }
    for key, val in known.items():
        if key in domain.lower():
            return val
    return domain


def extract_domain(url: str) -> str:
    m = re.search(r"://([^/]+)", url)
    return m.group(1) if m else url


# ── Access log ──────────────────────────────────────────────────────

def _log_path(store: str) -> Path:
    safe = re.sub(r"[^a-z0-9_]", "_", store.lower())
    return _LOG_DIR / f"{safe}.json"


def load_access_log(store: str) -> dict:
    path = _log_path(store)
    if path.exists():
        return json.loads(path.read_text())
    return {
        "store": store,
        "domain": "",
        "first_accessed": None,
        "last_accessed": None,
        "methods": [],
        "current_best": None,
        "extraction": {"jsonld_types": [], "selectors": {}, "notes": ""},
    }


def save_access_log(store: str, log: dict):
    (_LOG_DIR).mkdir(parents=True, exist_ok=True)
    _log_path(store).write_text(json.dumps(log, indent=2, default=str))


def update_access_log(store: str, method: str, status: str,
                      tool: str = "", response: str = "", domain: str = ""):
    log = load_access_log(store)
    now = datetime.now(timezone.utc).isoformat()
    if not log["first_accessed"]:
        log["first_accessed"] = now
    log["last_accessed"] = now
    if domain and not log["domain"]:
        log["domain"] = domain

    entry = {
        "method": method,
        "tool": tool,
        "status": status,
        "timestamp": now,
        "response": response[:200],
    }
    # Replace same method's last entry if identical status
    existing = [m for m in log["methods"] if m["method"] == method]
    if existing and existing[-1]["status"] == status and existing[-1]["response"] == response:
        pass
    else:
        log["methods"].append(entry)

    if status == "success":
        log["current_best"] = method

    save_access_log(store, log)
    return log


def update_extraction_notes(store: str, jsonld_types: list[str] | None = None,
                            selectors: dict | None = None, notes: str = ""):
    log = load_access_log(store)
    if jsonld_types:
        existing = set(log["extraction"]["jsonld_types"])
        existing.update(jsonld_types)
        log["extraction"]["jsonld_types"] = sorted(existing)
    if selectors:
        log["extraction"]["selectors"].update(selectors)
    if notes:
        log["extraction"]["notes"] = (log["extraction"]["notes"] + "\n" + notes).strip()
    save_access_log(store, log)


# ── Per-store skill generation ──────────────────────────────────────

SKILL_TEMPLATE = """# Store Access: {store}

## Domain
{domain}

## Access Methods (ranked)
{methods}

## Extraction
- JSON-LD types: {jsonld_types}
- CSS selectors: {selectors}
{extraction_notes}

## Rate Limits
{rate_limits}

## Last Tested
{last_tested}
"""


def generate_store_skill(store: str):
    log = load_access_log(store)
    if not log["methods"]:
        return

    ranked = sorted(log["methods"], key=lambda m: (
        0 if m["status"] == "success" else 1,
        ["fetch_page_html", "crawl4ai", "playwright", "extract_tavily"].index(m["method"])
        if m["method"] in ["fetch_page_html", "crawl4ai", "playwright", "extract_tavily"] else 99
    ))

    methods_lines = []
    for i, m in enumerate(ranked, 1):
        icon = "✅" if m["status"] == "success" else "❌"
        methods_lines.append(f"{i}. **{m['method']}** — {icon} {m['status']} ({m['tool']})")
        if m.get("response"):
            methods_lines.append(f"   Response: {m['response']}")

    jsonld = log["extraction"].get("jsonld_types", [])
    selectors = log["extraction"].get("selectors", {})
    sel_str = ", ".join(f"`{k}`: `{v}`" for k, v in selectors.items()) if selectors else "none yet"

    safe = re.sub(r"[^a-z0-9_]", "_", store.lower())
    skill_path = _SKILL_DIR / f"{safe}.md"
    skill_path.write_text(SKILL_TEMPLATE.format(
        store=store,
        domain=log.get("domain", "unknown"),
        methods="\n".join(methods_lines),
        jsonld_types=jsonld or "none found",
        selectors=sel_str,
        extraction_notes=f"- Notes: {log['extraction']['notes']}" if log["extraction"].get("notes") else "",
        rate_limits="Unknown. Add 1s delay between requests as default.",
        last_tested=log.get("last_accessed", "never"),
    ))
    logger.info("Store skill generated: %s", skill_path)
    return skill_path


# ── Fetch methods ───────────────────────────────────────────────────

def fetch_direct_http(url: str, timeout: int = 8) -> str | None:
    try:
        import requests
        resp = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            return None
        return resp.text
    except Exception as e:
        logger.debug("fetch_direct_http failed for %s: %s", url, e)
        return None


def fetch_playwright(url: str, timeout: int = 15) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                page.wait_for_timeout(2000)
                html = page.content()
                return html
            finally:
                browser.close()
    except Exception as e:
        logger.debug("fetch_playwright failed for %s: %s", url, e)
        return None


def fetch_crawl4ai(url: str, timeout: int = 20) -> str | None:
    try:
        from crawl4ai import AsyncWebCrawler
        import asyncio
        async def _crawl():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                return result.html if result else None
        return asyncio.run(_crawl())
    except Exception as e:
        logger.debug("fetch_crawl4ai failed for %s: %s", url, e)
        return None


def fetch_tavily_extract(url: str) -> str | None:
    try:
        from tools import extract_tavily
        results = extract_tavily([url])
        for r in results:
            if r.get("url") == url:
                return r.get("raw_content") or r.get("content") or None
        return None
    except Exception as e:
        logger.debug("fetch_tavily_extract failed for %s: %s", url, e)
        return None


# ── Dispatcher ──────────────────────────────────────────────────────

_METHODS = [
    ("fetch_page_html", "requests (tools.fetch_page_html)", fetch_direct_http),
    ("crawl4ai", "crawl4ai AsyncWebCrawler", fetch_crawl4ai),
    ("playwright", "playwright browser automation", fetch_playwright),
    ("extract_tavily", "Tavily extract API", fetch_tavily_extract),
]


def fetch_product_page(url: str) -> str | None:
    store = extract_store_name(url)
    domain = extract_domain(url)
    logger.info("Fetching product page for %s (%s)", store, domain)

    for method_name, tool_name, fn in _METHODS:
        html = fn(url)
        if html:
            update_access_log(store, method_name, "success",
                              tool=tool_name, response=f"got {len(html)} bytes",
                              domain=domain)
            generate_store_skill(store)
            logger.info("  %s succeeded (%d bytes)", method_name, len(html))
            return html
        update_access_log(store, method_name, "blocked",
                          tool=tool_name, response="no HTML returned",
                          domain=domain)

    logger.info("  all methods failed for %s", url)
    return None
