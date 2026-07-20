#!/usr/bin/env python3
"""
Sparrow — End-to-End Product Comparison Pipeline

Usage:
    python3 run.py "HP 64A toner cartridge"
    python3 run.py "Dell ink cartridge 32XL"

This simulates the full agent flow:
1. Search for product alternatives (stub without Brave API key)
2. Score each across 8 dimensions
3. Generate an HTML comparison report

With Brave Search API key configured, step 1 returns real results.
"""
import sys
import os
import json
from pathlib import Path

# Add agent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import search_brave
from scorer import score_batch, parse_price_score, parse_shipping_score, parse_quality_score, parse_vendor_score
from report_generator import generate_report


def parse_query(query: str) -> str:
    """Normalize the user query into a search term."""
    return query.strip()


def fetch_products(search_term: str) -> list[dict]:
    """
    Fetch product data from search.
    Returns list of dicts with product_name, vendor, url, and raw data.
    """
    results = search_brave(search_term, max_results=8)
    
    products = []
    if results["provider"] == "stub":
        # Return demo data for testing without API key
        products.extend([
            {
                "product_name": "HP 64A Toner (CC364A)",
                "vendor": "Amazon",
                "url": "https://amazon.com/hp-64a",
                "raw_price": 49.99,
                "shipping_days": 2,
                "free_shipping": True,
                "avg_rating": 4.3,
                "review_count": 1200,
                "trustpilot": 0,
                "has_warranty": True,
            },
            {
                "product_name": "HP 64A Toner (CC364A)",
                "vendor": "CDW",
                "url": "https://cdw.com/hp-64a",
                "raw_price": 89.99,
                "shipping_days": 3,
                "free_shipping": True,
                "avg_rating": 4.7,
                "review_count": 340,
                "trustpilot": 0,
                "has_warranty": True,
            },
            {
                "product_name": "HP 64A Toner (CC364A)",
                "vendor": "Staples",
                "url": "https://staples.com/hp-64a",
                "raw_price": 64.99,
                "shipping_days": 4,
                "free_shipping": False,
                "avg_rating": 4.1,
                "review_count": 890,
                "trustpilot": 0,
                "has_warranty": True,
            },
        ])
    elif results["provider"] == "brave":
        # Parse real Brave search results into product-like dicts
        # In a full implementation, you'd scrape each URL for price/vendor data
        # For now, use snippet text to extract basic info
        vendor_map = {
            "amazon": "Amazon",
            "ebay": "eBay",
            "cdw": "CDW",
            "staples": "Staples",
            "newegg": "Newegg",
            "bhphotovideo": "B&H Photo",
            "bestbuy": "Best Buy",
            "walmart": "Walmart",
            "overstock": "Overstock",
            "officedepot": "Office Depot",
        }
        
        for r in results["results"]:
            url_lower = r["url"].lower()
            snippet_lower = r.get("snippet", "").lower()
            combined = url_lower + " " + snippet_lower
            
            vendor = "Unknown"
            for key, val in vendor_map.items():
                if key in combined:
                    vendor = val
                    break
            
            products.append({
                "product_name": search_term,
                "vendor": vendor,
                "url": r["url"],
                "snippet": r.get("snippet", ""),
                "raw_price": None,
                "shipping_days": None,
                "free_shipping": False,
                "avg_rating": None,
                "review_count": 0,
                "trustpilot": 0,
                "has_warranty": False,
            })
    
    return products


def score_from_raw(products: list[dict]) -> list[dict]:
    """
    Convert raw product dicts into scored dicts with dimension scores.
    This is where the agent's LLM would normally inject qualitative scores.
    For now, we derive scores from available quantitative data.
    """
    prices = [p["raw_price"] for p in products if p.get("raw_price")]
    price_min = min(prices) if prices else 0
    price_max = max(prices) if prices else 1
    
    scored = []
    for p in products:
        scores = {}
        
        if p.get("raw_price") and price_max > price_min:
            scores["price"] = parse_price_score(p["raw_price"], (price_min, price_max))
        else:
            scores["price"] = 50  # unknown
        
        if p.get("avg_rating"):
            scores["quality"] = parse_quality_score(p["avg_rating"], p.get("review_count", 0))
        else:
            scores["quality"] = 50
        
        if p.get("shipping_days"):
            scores["shipping_speed"] = parse_shipping_score(
                p["shipping_days"], p.get("free_shipping", False)
            )
        else:
            scores["shipping_speed"] = 50
        
        if p.get("trustpilot") or p.get("has_warranty"):
            scores["vendor_reputation"] = parse_vendor_score(
                p.get("trustpilot", 0),
                has_warranty=p.get("has_warranty", False),
            )
        else:
            scores["vendor_reputation"] = 50
        
        # Default scores for dimensions we can't derive
        scores.setdefault("warranty_service", 70)
        scores.setdefault("sustainability", 40)
        scores.setdefault("secondhand_condition", 50)
        scores.setdefault("preference_alignment", 75)
        
        scored.append({
            "product_name": p["product_name"],
            "vendor": p["vendor"],
            "url": p["url"],
            "scores": scores,
            "metadata": {
                "price": p.get("raw_price", "?"),
                "shipping_days": p.get("shipping_days", "?"),
                "free_shipping": p.get("free_shipping", False),
            },
        })
    
    return scored


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run.py \"product query\"")
        print("Example: python3 run.py \"HP 64A toner cartridge\"")
        sys.exit(1)
    
    query = parse_query(sys.argv[1])
    print(f"🔍 Searching for: \"{query}\"")
    print()
    
    # Step 1: Fetch products
    raw_products = fetch_products(query)
    print(f"📦 Found {len(raw_products)} potential options")
    
    if not raw_products:
        print("❌ No products found. Configure Brave Search API key for real results.")
        sys.exit(1)
    
    # Step 2: Score products
    scored_inputs = score_from_raw(raw_products)
    scored = score_batch(scored_inputs)
    
    # Print summary
    print()
    print("📊 Scores:")
    for ps in scored:
        dim_map = {d.name: d.score for d in ps.dimensions}
        print(f"  #{ps.rank_in_batch} {ps.vendor}: {ps.total_weighted_score:.0f}/100 "
              f"(Price:{dim_map['price']:.0f} Quality:{dim_map['quality']:.0f} "
              f"Ship:{dim_map['shipping_speed']:.0f} Trust:{dim_map['vendor_reputation']:.0f})")
    
    # Step 3: Calculate savings
    prices = [p.get("metadata", {}).get("price", 0) for p in scored_inputs 
              if isinstance(p.get("metadata", {}).get("price"), (int, float))]
    if prices and len(prices) > 1:
        current_price = max(prices)
        best_price = min(prices)
        annual_savings = f"{(current_price - best_price) * 4:.2f}"
    elif prices:
        annual_savings = "?"
    else:
        annual_savings = "?"
    
    if annual_savings != "?":
        savings_data = {
            "annual_savings": annual_savings,
            "fee": f"{float(annual_savings) * 0.1:.2f}",
            "net_benefit": f"{float(annual_savings) * 0.9:.2f}",
        }
    else:
        savings_data = {
            "annual_savings": "?",
            "fee": "?",
            "net_benefit": "?",
        }
    
    # Step 4: Generate report
    report_html = generate_report(
        scored=scored,
        product_query=query,
        savings_data=savings_data,
    )
    
    # Save report
    safe_name = query.replace(" ", "_").lower()[:40]
    report_path = Path(__file__).parent / "reports" / f"report_{safe_name}.html"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report_html)
    
    print()
    print(f"✅ Report saved to: {report_path}")
    print(f"🐦 Sparrow pipeline complete.")


if __name__ == "__main__":
    main()
