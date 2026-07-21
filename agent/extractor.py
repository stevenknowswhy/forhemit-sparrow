"""
Extracts structured product metadata from web search snippets using regex/heuristics.

Takes Brave search result snippets (raw text) and extracts prices, ratings,
shipping info, warranty, and other signals. Returns a structured dict with
both the extracted values and flags indicating whether each field was found.

Also supports extracting structured data from full product page HTML
(Tavily extract) including JSON-LD schema.org markup and meta tags.

Usage:
    from extractor import extract_metadata
    meta = extract_metadata(snippet, extra_snippets)
    # → {"price": 49.99, "price_found": True, "rating": 4.3, ...}
"""
from __future__ import annotations
import re
import math
import json


def _all_text(snippet: str, extra_snippets: list[str]) -> str:
    return " ".join([snippet] + extra_snippets)


def extract_price(text: str) -> tuple[float | None, bool]:
    matches = re.findall(r'\$(\d+(?:,\d{3})*(?:\.\d{1,2})?)', text)
    if not matches:
        return None, False
    raw = matches[0].replace(",", "")
    try:
        return float(raw), True
    except ValueError:
        return None, False


def extract_rating(text: str) -> tuple[float | None, bool]:
    m = re.search(r'(\d\.?\d*)\s*(?:out\s*of|/)\s*5', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    m = re.search(r'rating[:\s]*(\d\.?\d*)\s*\/\s*\d', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    m = re.search(r'(\d\.\d)\s*(?:stars?\b|read|review)', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    m = re.search(r'(\d\.\d)\s*\(?\d', text)
    if m:
        return float(m.group(1)), True
    return None, False


def extract_shipping_days(text: str) -> tuple[int | None, bool]:
    m = re.search(r'(\d+)[-\s]*(?:business\s*)?day', text, re.IGNORECASE)
    if m:
        return int(m.group(1)), True
    return None, False


def has_free_shipping(text: str) -> bool:
    return "free shipping" in text.lower()


def extract_shipping_cost(text: str) -> tuple[float | None, bool]:
    m = re.search(r'(?:shipping|delivery|freight).{0,20}\$(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    m = re.search(r'\$(\d+(?:\.\d{2})?).{0,20}(?:shipping|delivery|freight)', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    return None, False


def has_warranty(text: str) -> tuple[bool, bool]:
    text_lower = text.lower()
    keywords = ["warranty", "guarantee", "protection plan", "coverage"]
    found = any(kw in text_lower for kw in keywords)
    return found, found


def has_return_policy(text: str) -> tuple[bool, bool]:
    text_lower = text.lower()
    keywords = ["return policy", "free returns", "money-back", "30-day return",
                "easy return", "hassle-free return"]
    found = any(kw in text_lower for kw in keywords)
    return found, found


def extract_eco_score(text: str) -> tuple[float, bool]:
    keywords = ["eco-friendly", "sustainable", "energy star", "recycled",
                "carbon neutral", "eco-conscious", "green product",
                "environmentally friendly", "renewable"]
    text_lower = text.lower()
    score = 0
    for kw in keywords:
        if kw in text_lower:
            score += 15
    found = score > 0
    return min(100, score), found


def extract_vendor_sentiment(text: str) -> tuple[float, bool]:
    positive = ["highly rated", "top-rated", "best seller", "customer favorite",
                "award winning", "#1", "excellent", "great value", "top quality",
                "trusted", "recommended"]
    negative = ["recall", "defect", "complaint", "poor quality", "issues",
                "problem", "negative", "disappointed", "failure", "counterfeit",
                "warning", "class action", "lawsuit"]
    text_lower = text.lower()
    pos_score = sum(1 for kw in positive if kw in text_lower)
    neg_score = sum(1 for kw in negative if kw in text_lower)
    score = 50 + pos_score * 10 - neg_score * 15
    found = pos_score > 0 or neg_score > 0
    return max(0, min(100, score)), found


def extract_in_stock(text: str) -> tuple[bool, bool]:
    in_stock_kw = ["in stock", "available", "ready to ship", "ships now"]
    out_stock_kw = ["out of stock", "backorder", "pre-order", "unavailable",
                    "discontinued", "temporarily unavailable"]
    text_lower = text.lower()
    if any(kw in text_lower for kw in out_stock_kw):
        return False, True
    if any(kw in text_lower for kw in in_stock_kw):
        return True, True
    return True, False


def _find_json_ld_blocks(html: str) -> list:
    pattern = r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    blocks = []
    for m in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
        try:
            data = json.loads(m.group(1).strip())
            blocks.append(data)
        except (json.JSONDecodeError, AttributeError):
            continue
    return blocks


def _walk_json_ld(data, depth=0) -> dict:
    if depth > 5 or not isinstance(data, (dict, list)):
        return {}
    result = {}
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        if "@graph" in item:
            for node in item["@graph"]:
                r = _walk_json_ld(node, depth + 1)
                result.update(r)
            continue
        type_ = item.get("@type", "")
        if isinstance(type_, list):
            type_ = type_[0] if type_ else ""
        type_ = str(type_)
        if "Product" in type_ or "ProductGroup" in type_:
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                result.update(_parse_jsonld_offer(offers))
            elif isinstance(offers, list):
                for o in offers:
                    result.update(_parse_jsonld_offer(o))
            brand = item.get("brand", {})
            if isinstance(brand, dict) and brand.get("name"):
                result["brand"] = brand["name"]
            for w_key in ("warranty", " WarrantyPromise"):
                w = item.get(w_key, {})
                if isinstance(w, dict):
                    dur = w.get("durationOfWarranty", {})
                    if isinstance(dur, dict):
                        dur_str = dur.get("value", "")
                        if "Year" in dur_str or "year" in dur_str:
                            result["warranty_months"] = 12
                            result["warranty_months_found"] = True
                        elif "Month" in dur_str:
                            result["warranty_months"] = 1
                            result["warranty_months_found"] = True
                    break
            for child_key in ("offers", "review", "aggregateRating"):
                child = item.get(child_key)
                if isinstance(child, dict):
                    r = _walk_json_ld(child, depth + 1)
                    result.update(r)
        elif "Offer" in type_:
            result.update(_parse_jsonld_offer(item))
        elif "ShippingDeliveryTime" in type_:
            handling = item.get("handlingTime", {})
            transit = item.get("transitTime", {})
            days = 0
            if isinstance(handling, dict):
                days += int(handling.get("value", 0))
            if isinstance(transit, dict):
                days += int(transit.get("value", 0))
            if days > 0:
                result["shipping_days"] = days
                result["shipping_days_found"] = True
        elif "WarrantyPromise" in type_:
            dur = item.get("durationOfWarranty", {})
            if isinstance(dur, dict):
                dur_str = dur.get("value", "")
                if "Year" in dur_str:
                    result["warranty_months"] = 12
                    result["warranty_months_found"] = True
            result["has_warranty"] = True
            result["warranty_found"] = True
        elif type_ in ("AggregateRating", "AggregateOffer"):
            result.update(_parse_jsonld_aggregate(item))
        elif type_ == "Review":
            review_rating = item.get("reviewRating", {})
            if isinstance(review_rating, dict) and review_rating.get("ratingValue"):
                pass
    return result


def _parse_jsonld_offer(offer: dict) -> dict:
    result = {}
    price = offer.get("price")
    if price is not None:
        try:
            result["price"] = float(price)
            result["price_found"] = True
        except (ValueError, TypeError):
            pass
    avail = offer.get("availability", "")
    if avail:
        result["in_stock"] = "InStock" in avail
        result["in_stock_found"] = True
    shipping = offer.get("shippingDetails", {})
    if isinstance(shipping, dict):
        dest = shipping.get("shippingDestination", {})
        cost = shipping.get("shippingCost", {})
        if isinstance(cost, dict):
            try:
                result["shipping_cost"] = float(cost.get("value", 0))
                result["shipping_cost_found"] = True
            except (ValueError, TypeError):
                pass
        if cost and cost.get("value") == "0":
            result["free_shipping"] = True
        delivery_time = shipping.get("deliveryTime", {})
        if isinstance(delivery_time, dict):
            r = _walk_json_ld(delivery_time, 1)
            result.update(r)
    return result


def _parse_jsonld_aggregate(data: dict) -> dict:
    result = {}
    rv = data.get("ratingValue")
    if rv is not None:
        try:
            result["rating"] = float(rv)
            result["rating_found"] = True
        except (ValueError, TypeError):
            pass
    rc = data.get("ratingCount") or data.get("reviewCount")
    if rc is not None:
        try:
            result["review_count"] = int(rc)
        except (ValueError, TypeError):
            pass
    return result


def _extract_meta_tags(html: str) -> dict:
    result = {}
    pattern = r'<meta\s+(?:property|name)=["\']([^"\']+)["\']\s+content=["\']([^"\']*)["\']'
    for m in re.finditer(pattern, html, re.IGNORECASE):
        prop = m.group(1).lower()
        val = m.group(2)
        if prop in ("og:price:amount", "product:price:amount", "twitter:data1"):
            try:
                result["price"] = float(val)
                result["price_found"] = True
            except ValueError:
                pass
        elif prop in ("og:availability", "product:availability"):
            result["in_stock"] = "in stock" in val.lower() or "instock" in val.lower()
            result["in_stock_found"] = True
        elif "brand" in prop:
            result["brand"] = val
        elif prop in ("product:retailer_item_id", "og:upc"):
            result["sku"] = val
    return result


def extract_page_content(content: str, raw_content: str | None = None) -> dict:
    text = content or raw_content or ""
    base = extract_metadata(snippet=text)
    if raw_content:
        for block in _find_json_ld_blocks(raw_content):
            r = _walk_json_ld(block)
            base.update(r)
        meta = _extract_meta_tags(raw_content)
        base.update(meta)
    if text:
        months, found = extract_warranty_length(text)
        if found:
            base["warranty_months"] = months
            base["warranty_months_found"] = True
        lo, hi, found = extract_shipping_range(text)
        if found:
            base["shipping_days_lo"] = lo
            base["shipping_days_hi"] = hi
            base["shipping_range_found"] = True
        certs, found = extract_eco_certifications(text)
        if found:
            base["eco_certifications"] = certs
            base["eco_certs_found"] = True
        threshold, found = extract_free_shipping_threshold(text)
        if found:
            base["free_ship_threshold"] = threshold
            base["free_ship_threshold_found"] = True
        has_eco, _ = extract_eco_score(text)
        if has_eco > 0:
            base["eco_score"] = has_eco
            base["eco_found"] = True
    return base


def extract_eco_keywords(text: str) -> list[str]:
    keywords = ["eco-friendly", "sustainable", "energy star", "recycled",
                "carbon neutral", "green", "renewable"]
    return [kw for kw in keywords if kw in text.lower()]


def extract_warranty_length(text: str) -> tuple[int | None, bool]:
    patterns = [
        (r'(\d+)[-\s]*(?:year|yr)[-\s]*(?:manufacturer|limited|full|extended)?\s*warranty', "year"),
        (r'(\d+)[-\s]*(?:month|mo)[-\s]*(?:manufacturer|limited|full|extended)?\s*warranty', "month"),
        (r'warranty[:\s]+(\d+)[-\s]*(?:year|yr)', "year"),
        (r'(\d+)[-\s]*year[-\s]*(?:guarantee|protection plan|coverage)', "year"),
    ]
    for pat_str, unit in patterns:
        m = re.search(pat_str, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            months = val * 12 if unit == "year" else val
            return months, True
    return None, False


def extract_shipping_range(text: str) -> tuple[int | None, int | None, bool]:
    m = re.search(r'ships?\s+(?:in\s+)?(\d+)[-\s]*(\d+)?(?:\s+business)?\s*(?:days?|business\s+days?)', text, re.IGNORECASE)
    if m:
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        return lo, hi, True
    return None, None, False


def extract_free_shipping_threshold(text: str) -> tuple[float | None, bool]:
    m = re.search(r'free\s+shipping\s+(?:on\s+)?(?:orders?\s+(?:over|above)\s+)?\$?(\d+(?:\.\d{2})?)', text, re.IGNORECASE)
    if m:
        return float(m.group(1)), True
    return None, False


def extract_eco_certifications(text: str) -> tuple[list[str], bool]:
    certs = ["energy star", "epeat", "rohs", "reach", "fsc certified",
             "blue angel", "tco certified", "climate neutral", "carbon neutral",
             "ecolabel", "green seal", "cradle to cradle", "epd"]
    found = [c for c in certs if c in text.lower()]
    return found, len(found) > 0


def extract_tavily_content(content: str) -> dict:
    title_end = content.find("\n")
    title = content[:title_end] if title_end > 0 else ""
    text = content[title_end+1:] if title_end > 0 else content

    result = extract_metadata(snippet=text, title=title)
    result["warranty_months"], result["warranty_months_found"] = extract_warranty_length(content)
    ship_lo, ship_hi, ship_range_found = extract_shipping_range(content)
    result["shipping_days_lo"] = ship_lo
    result["shipping_days_hi"] = ship_hi
    result["shipping_range_found"] = ship_range_found
    result["free_ship_threshold"], result["free_ship_threshold_found"] = extract_free_shipping_threshold(content)
    result["eco_certifications"], result["eco_certs_found"] = extract_eco_certifications(content)
    return result


def extract_metadata(
    snippet: str,
    extra_snippets: list[str] | None = None,
    title: str | None = None,
) -> dict:
    parts = [snippet]
    if title:
        parts.insert(0, title)
    if extra_snippets:
        parts.extend(extra_snippets)
    text = " ".join(parts)

    price, price_found = extract_price(text)
    rating, rating_found = extract_rating(text)
    ship_days, ship_days_found = extract_shipping_days(text)
    ship_cost, ship_cost_found = extract_shipping_cost(text)
    free_ship = has_free_shipping(text)
    warr, warr_found = has_warranty(text)
    ret, ret_found = has_return_policy(text)
    eco, eco_found = extract_eco_score(text)
    sentiment, sent_found = extract_vendor_sentiment(text)
    in_stock, stock_found = extract_in_stock(text)

    return {
        "price": price,
        "price_found": price_found,
        "rating": rating,
        "rating_found": rating_found,
        "shipping_days": ship_days,
        "shipping_days_found": ship_days_found,
        "free_shipping": free_ship,
        "shipping_cost": ship_cost,
        "shipping_cost_found": ship_cost_found,
        "has_warranty": warr,
        "warranty_found": warr_found,
        "has_return_policy": ret,
        "return_policy_found": ret_found,
        "eco_score": eco,
        "eco_found": eco_found,
        "vendor_sentiment": sentiment,
        "vendor_sentiment_found": sent_found,
        "in_stock": in_stock,
        "in_stock_found": stock_found,
    }
