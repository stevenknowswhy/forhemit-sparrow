# -*- coding: utf-8 -*-
"""
Sparrow — End-to-End Product Comparison Pipeline

Usage:
    python3 run.py "HP 64A toner cartridge"
    python3 run.py --rubric business "Dell 32XL ink"
    python3 run.py --rubric consumer --custom-weights '{"price": 0.35}' "item"

With Brave Search API key configured, step 1 returns real results.
"""
from __future__ import annotations
import sys
import os
import json
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import search, extract_tavily, TAVILY_API_KEY
from store_access import fetch_product_page, update_extraction_notes, extract_store_name
from extractor import _find_json_ld_blocks
from scorer import (
    score_batch, parse_price_score, parse_shipping_score,
    parse_quality_score, parse_vendor_score,
    get_preset_dim_keys, get_preset_weights, get_preset_labels,
    RUBRIC_PRESETS,
)
from extractor import extract_metadata, extract_tavily_content, extract_page_content
from report_generator import generate_report
from settings import load_settings
from validator import validate_batch, apply_validation, print_validation_summary
from judge import judge_batch


def parse_query(query: str) -> str:
    return query.strip()


VENDOR_MAP = {
    "amazon": "Amazon", "ebay": "eBay", "cdw": "CDW",
    "staples": "Staples", "newegg": "Newegg",
    "bhphotovideo": "B&H Photo", "bestbuy": "Best Buy",
    "walmart": "Walmart", "overstock": "Overstock",
    "officedepot": "Office Depot",
    "hp.com": "HP", "dell.com": "Dell",
    "lenovo": "Lenovo", "apple.com": "Apple",
    "samsung": "Samsung", "brother": "Brother",
    "precisionroller": "Precision Roller",
    "tonerworld": "Toner World",
    "google": "Google",
    "jet.com": "Jet",
    "rakuten": "Rakuten",
    "target": "Target",
    "lowes": "Lowe's",
    "homedepot": "Home Depot",
}


def _detect_vendor(url: str, snippet: str = "") -> str:
    combined = url.lower() + " " + snippet.lower()
    for key, val in VENDOR_MAP.items():
        if key in combined:
            return val
    return "Unknown"


def _build_product(title: str, url: str, snippet: str, extra_snippets: list[str],
                   raw_price=None, avg_rating=None, review_count=0, source="") -> dict:
    return {
        "product_name": title,
        "vendor": _detect_vendor(url, snippet) if not source else source,
        "url": url,
        "title": title,
        "snippet": snippet,
        "extra_snippets": extra_snippets,
        "raw_price": raw_price,
        "shipping_days": None,
        "free_shipping": False,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "trustpilot": 0,
        "has_warranty": False,
        "shipping_cost": None,
    }


def fetch_products(search_term: str) -> list[dict]:
    results = search(search_term, max_results=8)
    products = []

    if results["provider"] == "stub":
        products.extend([
            _build_product("HP 64A Toner (CC364A)", "https://amazon.com/hp-64a",
                           "HP 64A Toner cartridge. High quality, 4.3 stars, free shipping.",
                           ["In stock. 2-day shipping available."],
                           raw_price=49.99, avg_rating=4.3, review_count=1200, source="Amazon"),
            _build_product("HP 64A Toner (CC364A)", "https://cdw.com/hp-64a",
                           "HP 64A Toner for LaserJet. 4.7 stars, free shipping, trusted vendor.",
                           ["Authorized HP reseller. 3-year warranty included."],
                           raw_price=89.99, avg_rating=4.7, review_count=340, source="CDW"),
            _build_product("HP 64A Toner (CC364A)", "https://staples.com/hp-64a",
                           "HP 64A Toner. $8.99 shipping, 4.1 stars, in stock.",
                           ["Ships in 4 business days."],
                           raw_price=64.99, avg_rating=4.1, review_count=890, source="Staples"),
        ])

    elif results["provider"] == "serper":
        for s in results.get("shopping", []):
            products.append(_build_product(
                title=s["title"],
                url=s["url"],
                snippet=s.get("snippet", ""),
                extra_snippets=[],
                raw_price=s.get("price_value"),
                avg_rating=s.get("rating"),
                review_count=s.get("review_count", 0),
                source=s.get("source", ""),
            ))

        seen_urls = {p["url"] for p in products}
        for r in results.get("results", []):
            if r["url"] not in seen_urls:
                products.append(_build_product(
                    title=r["title"],
                    url=r["url"],
                    snippet=r.get("snippet", ""),
                    extra_snippets=r.get("extra_snippets", []),
                    avg_rating=r.get("rating"),
                    review_count=r.get("review_count", 0),
                ))
                seen_urls.add(r["url"])

    elif results["provider"] == "tavily":
        for r in results["results"]:
            content = r.get("content", "")
            tavily_meta = extract_tavily_content(content) if content else {}
            p = _build_product(
                title=r.get("title", search_term),
                url=r.get("url", ""),
                snippet=content,
                extra_snippets=[],
            )
            p["_tavily_meta"] = tavily_meta
            products.append(p)

    elif results["provider"] == "brave":
        for r in results["results"]:
            title = r.get("title", search_term)
            products.append(_build_product(
                title=title, url=r["url"],
                snippet=r.get("snippet", ""),
                extra_snippets=r.get("extra_snippets", []),
            ))

    _is_google_url = lambda u: "google.com/search" in u or "googleadservices" in u

    for p in products[:5]:
        url = p.get("url", "")
        if not url or _is_google_url(url):
            continue
        html = fetch_product_page(url)
        if not html:
            continue
        page_data = extract_page_content("", html)
        if any(v for v in page_data.values() if v):
            p["_page_data"] = page_data
            store = extract_store_name(url)
            jsonld_types = []
            for block in _find_json_ld_blocks(html):
                items = block if isinstance(block, list) else [block]
                for item in items:
                    if isinstance(item, dict):
                        t = item.get("@type", "")
                        if isinstance(t, list):
                            jsonld_types.extend(t)
                        elif t:
                            jsonld_types.append(t)
            update_extraction_notes(store, jsonld_types=jsonld_types)

    return products


def score_from_raw(products: list[dict], preset: str = "consumer") -> list[dict]:
    dim_keys = get_preset_dim_keys(preset)

    for p in products:
        meta = extract_metadata(
            p.get("snippet", ""),
            p.get("extra_snippets", []),
            title=p.get("title"),
        )
        p["_extracted"] = meta
        if p["raw_price"] is None and meta["price_found"]:
            p["raw_price"] = meta["price"]
        if p["shipping_days"] is None and meta["shipping_days_found"]:
            p["shipping_days"] = meta["shipping_days"]
        if not p["free_shipping"] and meta["free_shipping"]:
            p["free_shipping"] = True
        if p["shipping_cost"] is None and meta["shipping_cost_found"]:
            p["shipping_cost"] = meta["shipping_cost"]
        if not p["has_warranty"] and meta["warranty_found"]:
            p["has_warranty"] = meta["has_warranty"]
        if p["avg_rating"] is None and meta["rating_found"]:
            p["avg_rating"] = meta["rating"]

        if p.get("_page_data"):
            p["_page_data"].pop("price", None)
            p["_page_data"].pop("price_found", None)
            p["_page_data"].pop("rating", None)
            p["_page_data"].pop("rating_found", None)
            p["_page_data"].pop("review_count", None)
            meta.update(p["_page_data"])
            meta["_page_sourced"] = True

    prices = [p["raw_price"] for p in products if p.get("raw_price")]
    price_min = min(prices) if prices else 0
    price_max = max(prices) if prices else 1

    scored = []
    for p in products:
        scores = {}
        data_quality = {}

        raw_price = p.get("raw_price")
        shipping_days = p.get("shipping_days")
        free_shipping = p.get("free_shipping", False)
        shipping_cost = p.get("shipping_cost")
        avg_rating = p.get("avg_rating")
        review_count = p.get("review_count", 0)
        trustpilot = p.get("trustpilot", 0)
        has_warranty = p.get("has_warranty", False)
        meta = p.get("_extracted", {})

        # --- Consumer keys ---
        if "price" in dim_keys:
            if raw_price is not None and price_max > price_min:
                scores["price"] = parse_price_score(raw_price, (price_min, price_max))
                data_quality["price"] = True
            else:
                scores["price"] = 50
                data_quality["price"] = False

        if "shipping_speed" in dim_keys:
            if shipping_days is not None:
                scores["shipping_speed"] = parse_shipping_score(shipping_days, free_shipping)
                data_quality["shipping_speed"] = True
            elif meta.get("shipping_range_found"):
                lo = meta.get("shipping_days_lo", 3)
                hi = meta.get("shipping_days_hi", 7)
                avg = (lo + hi) / 2
                scores["shipping_speed"] = parse_shipping_score(avg, free_shipping or meta.get("free_shipping", False))
                data_quality["shipping_speed"] = True
            else:
                scores["shipping_speed"] = 50
                data_quality["shipping_speed"] = False

        if "vendor_reputation" in dim_keys:
            has_warranty_signal = has_warranty or meta.get("warranty_months") is not None
            if trustpilot or has_warranty_signal or meta.get("vendor_sentiment_found") or meta.get("return_policy_found"):
                scores["vendor_reputation"] = parse_vendor_score(
                    trustpilot, has_warranty=has_warranty_signal,
                    sentiment_score=meta.get("vendor_sentiment"),
                    has_return_policy=meta.get("has_return_policy", False),
                )
                data_quality["vendor_reputation"] = True
            else:
                scores["vendor_reputation"] = 50
                data_quality["vendor_reputation"] = False

        if "warranty_service" in dim_keys:
            warranty_months = meta.get("warranty_months")
            if warranty_months:
                base = min(100, 50 + warranty_months * 1.5)
                scores["warranty_service"] = max(50, base)
                data_quality["warranty_service"] = True
            elif has_warranty:
                scores["warranty_service"] = 65
                data_quality["warranty_service"] = meta.get("warranty_found", False)
            else:
                scores["warranty_service"] = 50
                data_quality["warranty_service"] = False

        if "secondhand_condition" in dim_keys:
            scores["secondhand_condition"] = 50
            data_quality["secondhand_condition"] = False

        if "preference_alignment" in dim_keys:
            scores["preference_alignment"] = 50
            data_quality["preference_alignment"] = False

        # --- Business keys ---
        if "unit_price" in dim_keys:
            if raw_price is not None and price_max > price_min:
                scores["unit_price"] = parse_price_score(raw_price, (price_min, price_max))
                data_quality["unit_price"] = True
            else:
                scores["unit_price"] = 50
                data_quality["unit_price"] = False

        if "logistics" in dim_keys:
            cost = shipping_cost if shipping_cost is not None else (0 if free_shipping else 5.0)
            has_cost_data = meta.get("shipping_cost_found", False) or meta.get("free_shipping", False)
            if has_cost_data and cost == 0:
                scores["logistics"] = 100
                data_quality["logistics"] = True
            elif has_cost_data and price_max > price_min:
                cost_range = (0, max(20, cost * 2))
                scores["logistics"] = parse_price_score(cost, cost_range)
                data_quality["logistics"] = True
            elif shipping_days is not None:
                scores["logistics"] = parse_shipping_score(shipping_days, free_shipping)
                data_quality["logistics"] = True
            else:
                scores["logistics"] = 50
                data_quality["logistics"] = False

        if "speed_reliability" in dim_keys:
            if shipping_days is not None:
                scores["speed_reliability"] = parse_shipping_score(shipping_days, free_shipping)
                data_quality["speed_reliability"] = True
            else:
                scores["speed_reliability"] = 50
                data_quality["speed_reliability"] = False

        if "supplier_trust" in dim_keys:
            if trustpilot or has_warranty or meta.get("vendor_sentiment_found") or meta.get("return_policy_found"):
                scores["supplier_trust"] = parse_vendor_score(
                    trustpilot, has_warranty=has_warranty,
                    sentiment_score=meta.get("vendor_sentiment"),
                    has_return_policy=meta.get("has_return_policy", False),
                )
                data_quality["supplier_trust"] = True
            else:
                scores["supplier_trust"] = 50
                data_quality["supplier_trust"] = False

        if "compatibility_risk" in dim_keys:
            scores["compatibility_risk"] = 75
            data_quality["compatibility_risk"] = False

        # --- Shared keys ---
        if "quality" in dim_keys:
            if avg_rating:
                scores["quality"] = parse_quality_score(avg_rating, review_count)
                data_quality["quality"] = True
            else:
                scores["quality"] = 50
                data_quality["quality"] = False

        if "sustainability" in dim_keys:
            certs = meta.get("eco_certifications", [])
            cert_score = min(100, len(certs) * 15)
            kw_score = meta.get("eco_score", 0)
            if certs:
                scores["sustainability"] = max(cert_score, kw_score)
                data_quality["sustainability"] = True
            elif meta.get("eco_found"):
                scores["sustainability"] = meta["eco_score"]
                data_quality["sustainability"] = True
            else:
                scores["sustainability"] = 40
                data_quality["sustainability"] = False

        scored.append({
            "product_name": p["product_name"],
            "vendor": p["vendor"],
            "url": p["url"],
            "scores": scores,
            "data_quality": data_quality,
            "metadata": {
                "price": p.get("raw_price", "?"),
                "shipping_days": p.get("shipping_days", "?"),
                "free_shipping": p.get("free_shipping", False),
                "shipping_cost": p.get("shipping_cost"),
            },
        })

    return scored


def main():
    parser = argparse.ArgumentParser(description="Sparrow product comparison pipeline")
    parser.add_argument("query", nargs="?", help="Product to search for")
    parser.add_argument("--rubric", choices=list(RUBRIC_PRESETS.keys()),
                        default=load_settings().get("rubric", "consumer"),
                        help="Rubric preset to use")
    parser.add_argument("--custom-weights", type=str, help="JSON dict of custom weights")
    parser.add_argument("--list-rubrics", action="store_true", help="List available rubric presets")
    parser.add_argument("--reference-vendor", type=str, default=None,
                        help="Name of current vendor to score alternatives relative to")
    parser.add_argument("--no-judge", action="store_true",
                        help="Skip AI judge pass")
    parser.add_argument("--judge-model", type=str, default=None,
                        help="Model to use for AI judge (default: PRIMARY_MODEL from .env)")
    parser.add_argument("--judge-threshold", choices=["strict", "moderate", "lenient"],
                        default="moderate",
                        help="Judge sensitivity (default: moderate)")
    args = parser.parse_args()

    if args.list_rubrics:
        print("Available rubric presets:")
        for key, preset in RUBRIC_PRESETS.items():
            print(f"  {key}: {preset['label']}")
            print(f"       {preset['description']}")
            for dk, dv in preset["dimensions"]:
                print(f"       {dv['label']:<28} {dv['weight']*100:>3.0f}%")
            print()
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    preset = args.rubric
    custom_weights = json.loads(args.custom_weights) if args.custom_weights else None
    weights = custom_weights if custom_weights else get_preset_weights(preset)

    preset_label = RUBRIC_PRESETS[preset]["label"]
    print(f"🔍 Searching for: \"{args.query}\"")
    print(f"📐 Rubric: {preset_label}")
    if custom_weights:
        print(f"⚙️  Custom weights applied")
    if args.reference_vendor:
        print(f"🎯 Reference vendor: {args.reference_vendor}")
    print()

    raw_products = fetch_products(args.query)
    print(f"📦 Found {len(raw_products)} potential options")

    if not raw_products:
        print("❌ No products found. Configure Brave Search API key for real results.")
        sys.exit(1)

    scored_inputs = score_from_raw(raw_products, preset=preset)

    # Build reference scores from a specific vendor if requested
    reference_scores = None
    if args.reference_vendor:
        ref = next((p for p in scored_inputs if p["vendor"].lower() == args.reference_vendor.lower()), None)
        if ref:
            reference_scores = ref["scores"]
            print(f"🎯 Scored relative to: {ref['vendor']} ({ref['product_name']})")

    scored = score_batch(scored_inputs, weights=weights)

    validation = validate_batch(scored, preset=preset)
    ai_validation: dict = {}
    if not args.no_judge:
        ai_validation = judge_batch(
            scored, scored_inputs, preset=preset,
            model=args.judge_model, threshold=args.judge_threshold,
        )
        # Apply AI confidence adjustments separately
        for key, ai_vr in ai_validation.items():
            if key == "__global__":
                continue
            for ps in scored:
                pkey = f"{ps.product_name}::{ps.vendor}"
                if pkey == key:
                    penalty = sum(
                        0.15 if f.severity == "error" else 0.08 if f.severity == "warning" else 0.03
                        for f in ai_vr.flags
                    )
                    ps.confidence = max(0.25, ps.confidence - penalty)

    scored = apply_validation(scored, validation)
    print()
    print_validation_summary(validation)

    print()
    print("📊 Scores:")
    labels = get_preset_labels(preset)
    for ps in scored:
        dim_map = {d.name: d.score for d in ps.dimensions}
        conf_badge = f" (confidence: {ps.confidence:.0%})" if ps.confidence < 1.0 else ""
        parts = [f"  #{ps.rank_in_batch} {ps.vendor}: {ps.total_weighted_score:.0f}/100{conf_badge}"]
        for dk, dl in labels.items():
            val = dim_map.get(dk, 0)
            dq = ps.data_quality.get(dk, False)
            marker = "*" if dq else ""
            parts.append(f"{dl}={val:.0f}{marker}")
        print(" (".join(parts) + ")")
    print()

    prices = [p.get("metadata", {}).get("price", 0) for p in scored_inputs
              if isinstance(p.get("metadata", {}).get("price"), (int, float))]
    if len(prices) > 1:
        current_price = max(prices)
        best_price = min(prices)
        annual = (current_price - best_price) * 4
        savings_data = {
            "annual_savings": f"{annual:.2f}",
            "baseline": f"{current_price * 4:.2f}",
            "fee": f"{annual * 0.1:.2f}",
            "net_benefit": f"{annual * 0.9:.2f}",
        }
    else:
        savings_data = {"annual_savings": "?", "fee": "?", "net_benefit": "?"}

    report_html = generate_report(
        scored=scored,
        product_query=args.query,
        savings_data=savings_data,
        preset=preset,
        validation=validation,
        ai_validation=ai_validation,
    )

    safe_name = f"{args.query}_{preset}".replace(" ", "_").lower()[:50]
    report_path = Path(__file__).parent / "reports" / f"report_{safe_name}.html"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report_html)

    print(f"✅ Report saved to: {report_path}")
    print(f"🐦 Sparrow pipeline complete.")


if __name__ == "__main__":
    main()
