"""
LLM-powered judge agent for Sparrow product comparisons.
Cross-checks scored products against raw source data to detect
semantic inconsistencies the rule-based validator cannot catch.

Features:
  - Per-product parallel evaluation via ThreadPoolExecutor
  - Structured output via json_object response_format
  - File-based result caching (24h TTL)
  - Adjustable sensitivity threshold (strict / moderate / lenient)
  - Graceful degradation when API key is missing
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

from validator import ValidationFlag, ValidationResult, PENALTY_MAP
from scorer import ProductScore, get_preset_labels

load_dotenv()

_AI_BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
_AI_API_KEY = os.getenv("AGNES_API_KEY", "")
_DEFAULT_MODEL = os.getenv("PRIMARY_MODEL", "agnes-2.0-flash")
_CACHE_PATH = Path(__file__).parent / ".judge_cache.json"
_CACHE_TTL = 86400  # 24 hours

_THRESHOLD_PROMPTS = {
    "strict": "Only flag CLEAR, unambiguous contradictions where the snippet directly contradicts a score. When in doubt, do NOT flag.",
    "moderate": "Flag likely inconsistencies where the snippet suggests a different score than assigned.",
    "lenient": "Flag any potential inconsistency, including subtle mismatches between snippet and scores.",
}
_THRESHOLD_TEMPS = {"strict": 0.0, "moderate": 0.1, "lenient": 0.3}

_DIM_DESCRIPTIONS = {
    "price": "How competitive the price is (higher = cheaper/better value)",
    "quality": "Product quality based on ratings, reviews, brand reputation",
    "shipping_speed": "How fast the product ships (higher = faster)",
    "vendor_reputation": "Trustworthiness of the seller/vendor",
    "warranty_service": "Warranty coverage and service quality",
    "sustainability": "Environmental friendliness of product/vendor",
    "secondhand_condition": "Condition quality if secondhand/refurbished",
    "preference_alignment": "How well the product matches user preferences",
    "logistics": "Shipping cost and delivery reliability",
    "supplier_trust": "Supplier reliability and trust signals",
    "compatibility_risk": "Risk of incompatibility with intended use",
}


def _make_client() -> OpenAI | None:
    if not _AI_API_KEY:
        return None
    return OpenAI(base_url=_AI_BASE_URL, api_key=_AI_API_KEY)


def _cache_key(ps: ProductScore, preset: str, threshold: str) -> str:
    raw = f"{ps.product_name}|{ps.vendor}|{ps.url}|{preset}|{threshold}"
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


def _has_data(ps: ProductScore) -> bool:
    return any(d.score != 50 for d in ps.dimensions)


_CROSS_VENDORS = {
    "hp": "HP Inc.",
    "dell": "Dell Technologies",
    "lenovo": "Lenovo",
    "target": "Target",
    "walmart": "Walmart",
    "amazon": "Amazon",
    "bestbuy": "Best Buy",
    "staples": "Staples",
    "lowes": "Lowe's",
    "homedepot": "The Home Depot",
    "officedepot": "Office Depot",
    "officemax": "OfficeMax",
    "newegg": "Newegg",
    "bhphotovideo": "B&H Photo Video",
}


def _vendor_brand(vendor: str) -> str:
    """Map short vendor name to a well-known brand label."""
    return _CROSS_VENDORS.get(vendor.lower().replace(" ", "").replace("'", ""), vendor)


def _build_cross_prompt(
    scored: list[ProductScore],
    raw_products: list[dict],
    labels: dict[str, str],
    threshold: str,
) -> str:
    """Build prompt for cross-product inconsistency detection."""
    raw_by_url = {r.get("url", ""): r for r in raw_products}

    rows = []
    for i, ps in enumerate(scored, 1):
        raw = raw_by_url.get(ps.url, {})
        price_raw = raw.get("raw_price", "N/A")
        rating_raw = raw.get("avg_rating", "N/A")
        brand = _vendor_brand(ps.vendor)

        dim_strs = [f"{labels.get(d.name, d.name)}={d.score:.0f}" for d in ps.dimensions]
        rows.append(
            f"{i}. {ps.product_name} | vendor={brand} | price=${price_raw} | "
            f"rating={rating_raw} | {', '.join(dim_strs)}"
        )

    table = "\n".join(rows)

    return f"""\
You are a strict product comparison auditor. Below are products scored across dimensions (0-100, higher=better) with raw source data.

Compare products against each other for cross-product inconsistencies:

## 1. Price vs Price-Score
- Two products with raw prices within $5 of each other but price scores differing by >15 points
- A product with a lower raw price ($) receiving a lower price score than a more expensive one

## 2. Rating vs Quality-Score
- Two products with ratings within 0.3 stars of each other but quality scores differing by >15 points
- A product with rating >4.0 but quality score <50, or rating <3.0 but quality score >70

## 3. Vendor Reputation Consistency
- An unknown vendor scoring higher on vendor_reputation or quality than established brands (HP, Dell, Lenovo, Amazon, Target, Walmart, Best Buy, Staples)
- Two products from the same vendor with scores differing by >25 points on the same dimension

## 4. Score Range Anomalies
- ALL dimensions for a single product clustered in a tight range (e.g. all 40-60) — possible default-score artifact
- A single dimension scoring >80 or <20 while all other dimensions for that product sit in 40-60 range — extreme outlier

## 5. Data Quality Clues
- Products with identical or near-identical raw price AND rating but with very different overall scores
- A dimension flagged as data-backed yet scored exactly 50 (the default) — data may not have been applied

{_THRESHOLD_PROMPTS.get(threshold, _THRESHOLD_PROMPTS["moderate"])}

Product batch:
{table}

Output a JSON object with EXACTLY this structure:
{{"flags": [{{"product_index": 1, "severity": "warning", "field": "quality", "message": "...", "suggestion": "..."}}]}}
- "product_index" MUST match the list number (1-based) from the batch above. Use 0 for a general batch observation.
- "severity": "info" | "warning" | "error"
- "field": dimension name or "general"
- "message": brief explanation of what is inconsistent
- "suggestion": what action to take to verify or correct
- Return {{"flags": []}} if no cross-product issues found.
"""


def _parse_cross_flags(
    content: str,
    scored: list[ProductScore],
) -> dict[str, list[ValidationFlag]]:
    """Parse cross-product comparison response into per-product flag lists."""
    try:
        data = json.loads(content)
        items = data if isinstance(data, list) else data.get("flags", [])
    except json.JSONDecodeError:
        import re
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return {}
        try:
            data = json.loads(m.group())
            items = data if isinstance(data, list) else data.get("flags", [])
        except json.JSONDecodeError:
            return {}

    by_product: dict[str, list[ValidationFlag]] = {}
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        idx = item.get("product_index", 0)
        if not isinstance(idx, int) or idx < 1 or idx > len(scored):
            continue
        ps = scored[idx - 1]
        key = f"{ps.product_name}::{ps.vendor}"
        flag = ValidationFlag(
            severity=item.get("severity", "info"),
            product_vendor=f"{ps.product_name} ({ps.vendor})",
            field=item.get("field", "general"),
            message=item.get("message", ""),
            suggestion=item.get("suggestion", ""),
            source="ai",
        )
        by_product.setdefault(key, []).append(flag)
    return by_product


def _judge_cross_products(
    client: OpenAI,
    scored: list[ProductScore],
    raw_products: list[dict],
    labels: dict[str, str],
    model: str,
    threshold: str,
) -> dict[str, list[ValidationFlag]]:
    """Run a single LLM call comparing all products for cross-product inconsistencies."""
    prompt = _build_cross_prompt(scored, raw_products, labels, threshold)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strict product comparison auditor. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=_THRESHOLD_TEMPS.get(threshold, 0.1),
            max_tokens=1500,
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"    ⚠️  Cross-product judge error: {e}")
        return {}
    return _parse_cross_flags(content, scored)


def _build_product_prompt(
    ps: ProductScore,
    raw: dict,
    labels: dict[str, str],
    threshold: str,
) -> str:
    snippet = raw.get("snippet", "") or ""
    extra = raw.get("extra_snippets", [])
    all_text = snippet + " " + "; ".join(extra[:3])
    raw_price = raw.get("raw_price", "N/A")
    rating = raw.get("avg_rating", "N/A")
    meta = ps.metadata
    price = meta.get("price", "N/A")
    shipping = meta.get("shipping_days", "N/A")

    dim_lines = []
    for d in ps.dimensions:
        desc = _DIM_DESCRIPTIONS.get(d.name, "")
        dim_lines.append(f"  - {labels.get(d.name, d.name)}: {d.score:.0f}/100 ({desc})")

    return f"""\
Product: {ps.product_name}
Vendor: {ps.vendor}
Price: ${price}  (raw source: ${raw_price})
Shipping: {shipping} days
Rating from source: {rating}
URL: {ps.url}

Scores (0-100, higher = better):
{chr(10).join(dim_lines)}

Raw source text:
{all_text[:800]}

{_THRESHOLD_PROMPTS.get(threshold, _THRESHOLD_PROMPTS["moderate"])}

Check each score against the raw text for clear contradictions. Consider:
- Price: text mentions "free shipping" or discount but shipping_cost > 0 or price score is low?
- Quality: rating/review count in text vs quality score?
- Shipping: "next day" or "2-day" but shipping speed score low? Or "ships in 5-7 days" but score high?
- Vendor: "authorized reseller" but vendor reputation low? Unknown vendor but score high?
- Warranty: explicit warranty mention but warranty score low? No mention but score high?
- Secondhand: "refurbished" / "open box" but secondhand_condition treating it as new?
- General: any factual claim that contradicts a score direction

Output a JSON object with EXACTLY this structure:
{{"flags": [{{"severity": "warning", "field": "price", "message": "...", "suggestion": "..."}}]}}
Return {{"flags": []}} if no issues found.
Valid severity: "info" (minor), "warning" (moderate), "error" (strong contradiction)
Field must match a score dimension name (e.g. "price", "quality") or "general".
"""


def _judge_product(
    client: OpenAI,
    ps: ProductScore,
    raw: dict,
    labels: dict[str, str],
    model: str,
    threshold: str,
    cache: dict,
) -> list[ValidationFlag]:
    ckey = _cache_key(ps, list(labels.values())[0] if labels else "unknown", threshold)
    cached = cache.get(ckey)
    if cached:
        age = time.time() - cached.get("cached_at", 0)
        if age < _CACHE_TTL:
            return [
                ValidationFlag(
                    severity=f["severity"],
                    product_vendor=f"{ps.product_name} ({ps.vendor})",
                    field=f["field"],
                    message=f["message"],
                    suggestion=f["suggestion"],
                    source="ai",
                )
                for f in cached.get("flags", [])
            ]

    prompt = _build_product_prompt(ps, raw, labels, threshold)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strict, objective product data judge. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=_THRESHOLD_TEMPS.get(threshold, 0.1),
            max_tokens=1000,
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        print(f"    ⚠️  Judge error for {ps.product_name}: {e}")
        return []

    flags = _parse_flags(content, ps)
    cache[ckey] = {
        "flags": [{"severity": f.severity, "field": f.field, "message": f.message, "suggestion": f.suggestion} for f in flags],
        "cached_at": time.time(),
    }
    return flags


def _parse_flags(content: str, ps: ProductScore) -> list[ValidationFlag]:
    try:
        data = json.loads(content)
        items = data if isinstance(data, list) else data.get("flags", [])
    except json.JSONDecodeError:
        import re
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group())
            items = data if isinstance(data, list) else data.get("flags", [])
        except json.JSONDecodeError:
            return []

    flags = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        flags.append(ValidationFlag(
            severity=item.get("severity", "info"),
            product_vendor=f"{ps.product_name} ({ps.vendor})",
            field=item.get("field", "general"),
            message=item.get("message", ""),
            suggestion=item.get("suggestion", ""),
            source="ai",
        ))
    return flags


def judge_batch(
    scored: list[ProductScore],
    raw_products: list[dict],
    preset: str = "consumer",
    model: str | None = None,
    threshold: str = "moderate",
) -> dict[str, ValidationResult]:
    """Run LLM judge pass over scored products.

    Evaluates each product independently in parallel, caches results,
    and returns a dict of ValidationResult (same format as validator.py).

    Returns empty dict if no API key configured or all products fail.
    """
    client = _make_client()
    if not client:
        print("  ⚠️  Judge agent: no AI API key configured, skipping")
        return {}

    model = model or _DEFAULT_MODEL
    labels = get_preset_labels(preset)
    cache = _load_cache()

    raw_by_url = {r.get("url", ""): r for r in raw_products}

    results: dict[str, ValidationResult] = {}
    global_flags: list[ValidationFlag] = []

    judged = [ps for ps in scored if _has_data(ps)]
    skipped = len(scored) - len(judged)
    if skipped:
        print(f"  🤖 Judge agent: skipping {skipped}/{len(scored)} product(s) (no data)")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for ps in judged:
            raw = raw_by_url.get(ps.url, {})
            future = executor.submit(
                _judge_product, client, ps, raw, labels, model, threshold, cache
            )
            futures[future] = ps

        for future in as_completed(futures):
            ps = futures[future]
            flags = future.result()
            if not flags:
                continue
            key = f"{ps.product_name}::{ps.vendor}"
            adjusted = 1.0
            for f in flags:
                adjusted -= PENALTY_MAP.get(f.severity, 0.03)
            results[key] = ValidationResult(
                product_name=ps.product_name,
                vendor=ps.vendor,
                flags=flags,
                adjusted_confidence=max(0.25, adjusted),
            )

    _save_cache(cache)

    flag_count = sum(len(vr.flags) for vr in results.values())
    cached_count = sum(
        1 for ps in scored
        if _load_cache().get(_cache_key(ps, list(labels.values())[0] if labels else "", threshold))
    )
    if flag_count:
        print(f"  🤖 Judge agent: {flag_count} AI flag(s) across {len(results)} product(s)"
              f"  (model: {model}, threshold: {threshold})")

    cross_flags_by_key = _judge_cross_products(
        client, scored, raw_products, labels, model, threshold
    )
    if cross_flags_by_key:
        cross_total = sum(len(v) for v in cross_flags_by_key.values())
        print(f"  🔄 Cross-product comparison: {cross_total} inconsistency flag(s)"
              f" across {len(cross_flags_by_key)} product(s)")
        for ckey, cflags in cross_flags_by_key.items():
            if ckey in results:
                results[ckey].flags.extend(cflags)
                adj = sum(PENALTY_MAP.get(f.severity, 0.03) for f in cflags)
                results[ckey].adjusted_confidence = max(0.25, results[ckey].adjusted_confidence - adj)
            else:
                match = next((ps for ps in scored if f"{ps.product_name}::{ps.vendor}" == ckey), None)
                if match:
                    adjusted = 1.0 - sum(PENALTY_MAP.get(f.severity, 0.03) for f in cflags)
                    results[ckey] = ValidationResult(
                        product_name=match.product_name,
                        vendor=match.vendor,
                        flags=cflags,
                        adjusted_confidence=max(0.25, adjusted),
                    )

    if global_flags:
        results["__global__"] = ValidationResult(
            product_name="__global__", vendor="__global__",
            flags=global_flags, adjusted_confidence=1.0,
        )

    return results
