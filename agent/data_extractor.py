"""
LLM-powered data extraction pass for Sparrow product comparisons.

Uses the same Agnes AI / OpenAI-compatible client as judge.py to extract
structured product data (shipping, warranty, sustainability, vendor reputation)
from Tavily content, product page text, and search snippets — filling the
data gaps that regex and JSON-LD extraction miss.

Falls back gracefully when no API key is configured.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_AI_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
_AI_API_KEY = os.getenv("AGNES_API_KEY", "")
_DEFAULT_MODEL = os.getenv("PRIMARY_MODEL", "agnes-2.0-flash")
_CACHE_PATH = Path(__file__).parent / ".data_extract_cache.json"
_CACHE_TTL = 86400  # 24 hours

_FIELDS_TO_EXTRACT = [
    "shipping_days",
    "shipping_cost",
    "free_shipping",
    "warranty_months",
    "has_warranty",
    "vendor_sentiment",
    "eco_score",
    "eco_certifications",
]

_FIELD_MAP = {
    "shipping_days": "shipping_days_found",
    "shipping_cost": "shipping_cost_found",
    "free_shipping": None,
    "warranty_months": "warranty_months_found",
    "has_warranty": "warranty_found",
    "vendor_sentiment": "vendor_sentiment_found",
    "eco_score": "eco_found",
    "eco_certifications": "eco_certs_found",
}


def _make_client() -> OpenAI | None:
    if not _AI_API_KEY:
        return None
    return OpenAI(base_url=_AI_BASE_URL, api_key=_AI_API_KEY)


def _cache_key(product: dict) -> str:
    raw = f"{product.get('product_name', '')}|{product.get('vendor', '')}|{product.get('url', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.write_text(json.dumps(cache, indent=2))


def _has_source_text(product: dict) -> bool:
    if product.get("_page_html"):
        return True
    if product.get("_tavily_meta"):
        return True
    snippet = product.get("snippet") or ""
    extra = product.get("extra_snippets") or []
    combined = snippet + " " + " ".join(extra[:3])
    if len(combined) > 100:
        return True
    return False


def _assemble_source_text(product: dict) -> str:
    parts = []
    html = product.get("_page_html")
    if html:
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 100:
            parts.append(f"[PRODUCT PAGE TEXT]\n{text[:3000]}")
    if not parts:
        tavily = product.get("_tavily_meta")
        if tavily:
            tavily_text = " ".join(str(v) for v in tavily.values() if isinstance(v, str))
            if tavily_text:
                parts.append(f"[TAVILY CONTENT]\n{tavily_text[:2000]}")
    if not parts:
        snippet = product.get("snippet") or ""
        extra = product.get("extra_snippets") or []
        combined = snippet + " " + " ".join(extra[:5])
        if combined.strip():
            parts.append(f"[SEARCH TEXT]\n{combined[:2000]}")
    return "\n\n".join(parts)


def _build_extraction_prompt(product: dict, source_text: str) -> str:
    return f"""\
Extract structured product data from the text below. CRITICAL RULES:
- ONLY return a field if you see SPECIFIC EXPLICIT EVIDENCE in the text.
- NEVER return default/placeholder values. If you don't see evidence, OMIT the field entirely.
- Return ONLY valid JSON. Return {{}} if you find no relevant data.

Product: {product.get('product_name', 'Unknown')}
Vendor: {product.get('vendor', 'Unknown')}
URL: {product.get('url', '')}

Extract ONLY if explicitly stated:
1. shipping_days — specific delivery time in business days (e.g. "ships in 3-5 days")
2. shipping_cost — specific dollar cost for shipping (e.g. "$5.99 shipping")
3. free_shipping — only if "free shipping" is explicitly mentioned
4. warranty_months — specific warranty duration (e.g. "1-year warranty", "90 day guarantee")
5. has_warranty — only if a warranty, guarantee, or protection plan is explicitly mentioned
6. vendor_sentiment — score 0-100 based on specific vendor reputation signals
7. eco_score — score 0-100 based on specific sustainability certifications or claims
8. eco_certifications — only recognized certifications (e.g. "Energy Star")

For each field, provide:
- "value": the extracted value
- "confidence": "high" (explicitly stated) or "medium" (clearly implied); OMIT if uncertain
- "source_text": the exact supporting phrase from the text

Source text:
{source_text[:3000]}

Output format:
{{"shipping_days": {{"value": 5, "confidence": "high", "source_text": "ships in 5-7 business days"}}}}
Return {{}} if you cannot extract any relevant data."""  # noqa: E501


def _parse_extraction(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        import re
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return {}
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict):
        return {}
    return data


def _extract_product(client: OpenAI, product: dict, model: str, cache: dict) -> dict:
    if not _has_source_text(product):
        return {}

    ckey = _cache_key(product)
    cached = cache.get(ckey)
    if cached:
        age = time.time() - cached.get("cached_at", 0)
        if age < _CACHE_TTL:
            return cached.get("meta", {})

    source_text = _assemble_source_text(product)
    if len(source_text.strip()) < 20:
        return {}

    prompt = _build_extraction_prompt(product, source_text)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You extract structured product data from text. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=1000,
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"    ⚠️  LLM extract error for {product.get('product_name', '?')}: {e}")
        return {}

    parsed = _parse_extraction(content)
    meta = _llm_to_meta(parsed)

    cache[ckey] = {"meta": meta, "cached_at": time.time()}
    return meta


def _llm_to_meta(parsed: dict) -> dict:
    meta = {}
    for field in _FIELDS_TO_EXTRACT:
        entry = parsed.get(field, {})
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        confidence = entry.get("confidence")
        if value is None or confidence is None:
            continue
        if confidence not in ("high", "medium"):
            continue
        if isinstance(value, bool) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, (int, float)) and field == "vendor_sentiment" and value == 50:
            continue
        meta[field] = value
        flag_field = _FIELD_MAP[field]
        if flag_field:
            meta[flag_field] = True
        meta.setdefault("_llm_sourced", []).append(field)
    return meta


def extract_batch(products: list[dict], model: str | None = None) -> list[dict]:
    """Run LLM extraction pass over product list.

    Returns a list of meta dicts in the same order as products.
    Products with no source text or when API key is missing get empty dicts.
    """
    client = _make_client()
    if not client:
        return [{} for _ in products]

    model = model or _DEFAULT_MODEL
    cache = _load_cache()
    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for p in products:
            if not _has_source_text(p):
                results.append({})
                continue
            future = executor.submit(_extract_product, client, p, model, cache)
            futures[future] = len(results)
            results.append(None)

        for future in as_completed(futures):
            idx = futures[future]
            meta = future.result()
            results[idx] = meta

    results = [r if r is not None else {} for r in results]

    extracted = sum(1 for r in results if r.get("_llm_sourced"))
    if extracted:
        print(f"  🤖 LLM data extraction: enriched {extracted}/{len(products)} product(s)  (model: {model})")

    _save_cache(cache)
    return results
