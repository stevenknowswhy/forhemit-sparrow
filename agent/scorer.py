"""
8-Dimension Rubric Scorer for Sparrow product comparisons.

Scores product alternatives across 8 dimensions (0-100 each),
computes a weighted total, and returns a structured score dict.

Dimensions (default weights sum to 100):
  1. Price (total landed cost)        — 25%
  2. Quality / reliability            — 20%
  3. Shipping speed / availability    — 15%
  4. Vendor reputation / trust        — 15%
  5. Warranty / service terms         — 10%
  6. Sustainability / eco-impact      —  5%
  7. Secondhand condition             —  5%  (only for used/refurb items)
  8. Preference alignment             —  5%  (user-specified priorities)

Weights are configurable per job via the `weights` parameter.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Dimension definitions ───────────────────────────────────────────

DIMENSIONS = [
    "price",
    "quality",
    "shipping_speed",
    "vendor_reputation",
    "warranty_service",
    "sustainability",
    "secondhand_condition",
    "preference_alignment",
]

DEFAULT_WEIGHTS = {
    "price": 0.25,
    "quality": 0.20,
    "shipping_speed": 0.15,
    "vendor_reputation": 0.15,
    "warranty_service": 0.10,
    "sustainability": 0.05,
    "secondhand_condition": 0.05,
    "preference_alignment": 0.05,
}

DIM_LABELS = {
    "price": "Price (Landed Cost)",
    "quality": "Quality / Reliability",
    "shipping_speed": "Shipping Speed",
    "vendor_reputation": "Vendor Reputation",
    "warranty_service": "Warranty / Service",
    "sustainability": "Sustainability",
    "secondhand_condition": "Secondhand Condition",
    "preference_alignment": "Preference Alignment",
}


# ── Data structures ─────────────────────────────────────────────────

@dataclass
class DimensionScore:
    """Score for a single dimension."""
    name: str
    score: float       # 0-100
    weight: float      # 0-1
    weighted_score: float
    rationale: str = ""


@dataclass
class ProductScore:
    """Complete rubric evaluation for one product."""
    product_name: str
    vendor: str
    url: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    total_weighted_score: float = 0.0
    rank_in_batch: int = 1
    is_secondhand: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "product_name": self.product_name,
            "vendor": self.vendor,
            "url": self.url,
            "dimensions": [asdict(d) for d in self.dimensions],
            "total_weighted_score": round(self.total_weighted_score, 2),
            "rank_in_batch": self.rank_in_batch,
            "is_secondhand": self.is_secondhand,
            "metadata": self.metadata,
        }


# ── Core scorer ─────────────────────────────────────────────────────

def score_product(
    product_name: str,
    vendor: str,
    url: str = "",
    scores: Optional[dict[str, float]] = None,
    weights: Optional[dict[str, float]] = None,
    is_secondhand: bool = False,
    secondhand_grade: Optional[str] = None,
    rationale: Optional[dict[str, str]] = None,
    metadata: Optional[dict] = None,
) -> ProductScore:
    """
    Score a single product across the 8-dimension rubric.

    Args:
        product_name: Human-readable product name
        vendor: Vendor / seller name
        url: Product page URL
        scores: Dict of dimension scores (0-100). Missing dims default to 50.
        weights: Dict of dimension weights. Defaults to DEFAULT_WEIGHTS.
        is_secondhand: Whether this is a used/refurb item
        secondhand_grade: Condition grade (Excellent, Good, Fair, Acceptable)
        rationale: Dict of dimension → explanation strings
        metadata: Extra fields (price, shipping_cost, etc.)

    Returns:
        ProductScore with all dimensions computed and weighted total.
    """
    weights = weights or DEFAULT_WEIGHTS.copy()
    scores = scores or {}
    rationale = rationale or {}
    metadata = metadata or {}

    # Secondhand condition penalty
    if is_secondhand and secondhand_grade:
        grade_multipliers = {
            "excellent": 0.9,
            "good": 0.7,
            "fair": 0.5,
            "acceptable": 0.3,
        }
        mult = grade_multipliers.get(secondhand_grade.lower(), 0.5)
        scores["secondhand_condition"] = min(100, scores.get("secondhand_condition", 50) * mult)

    dimensions = []
    total_weighted = 0.0
    total_weight = 0.0

    for dim in DIMENSIONS:
        dim_score = scores.get(dim, 50.0)
        # Clamp 0-100
        dim_score = max(0.0, min(100.0, float(dim_score)))
        w = weights.get(dim, 0.0)
        weighted = dim_score * w
        total_weighted += weighted
        total_weight += w

        dimensions.append(DimensionScore(
            name=dim,
            score=round(dim_score, 1),
            weight=w,
            weighted_score=round(weighted, 2),
            rationale=rationale.get(dim, ""),
        ))

    # Normalize by actual weight sum (in case some dims have 0 weight)
    if total_weight > 0:
        total_weighted /= total_weight

    return ProductScore(
        product_name=product_name,
        vendor=vendor,
        url=url,
        dimensions=dimensions,
        total_weighted_score=round(total_weighted, 2),
        is_secondhand=is_secondhand,
        metadata=metadata,
    )


def score_batch(products: list[dict], weights: Optional[dict] = None) -> list[ProductScore]:
    """
    Score a batch of products and rank them.

    Each product dict should have at least:
      - product_name (str)
      - vendor (str)
      - scores (dict[str, float]) — dimension scores 0-100

    Optional fields per product:
      - url, is_secondhand, secondhand_grade, rationale, metadata

    Returns:
        Sorted list of ProductScore objects (highest score first),
        with rank_in_batch set.
    """
    scored = []
    for p in products:
        ps = score_product(
            product_name=p["product_name"],
            vendor=p["vendor"],
            url=p.get("url", ""),
            scores=p.get("scores", {}),
            weights=weights,
            is_secondhand=p.get("is_secondhand", False),
            secondhand_grade=p.get("secondhand_grade"),
            rationale=p.get("rationale", {}),
            metadata=p.get("metadata", {}),
        )
        scored.append(ps)

    # Sort by total score descending
    scored.sort(key=lambda x: x.total_weighted_score, reverse=True)

    # Assign ranks
    for i, ps in enumerate(scored, 1):
        ps.rank_in_batch = i

    return scored


# ── Convenience: parse raw product data into scores ─────────────────

def parse_price_score(raw_price: float, price_range: tuple[float, float]) -> float:
    """
    Convert a raw price to a 0-100 score based on observed price range.
    Lower price = higher score.
    
    Args:
        raw_price: The actual price of this product
        price_range: (min_price, max_price) from the batch
        
    Returns:
        Score 0-100
    """
    lo, hi = price_range
    if lo == hi:
        return 100.0  # all same price
    # Linear interpolation: cheapest = 100, most expensive = 0
    score = 100.0 * (1.0 - (raw_price - lo) / (hi - lo))
    return max(0.0, min(100.0, score))


def parse_shipping_score(days: int, free_shipping: bool = False) -> float:
    """
    Convert shipping info to a 0-100 score.
    
    Args:
        days: Estimated delivery days
        free_shipping: Whether shipping is free
        
    Returns:
        Score 0-100
    """
    score = 100.0 - (days * 8)  # lose 8 pts per day
    if free_shipping:
        score += 15  # bonus for free shipping
    return max(0.0, min(100.0, score))


def parse_quality_score(avg_rating: float, review_count: int = 0) -> float:
    """
    Convert star rating + review count to a 0-100 score.
    
    Args:
        avg_rating: Average star rating (1-5)
        review_count: Number of reviews
        
    Returns:
        Score 0-100
    """
    # Star rating component (max 70)
    rating_score = (avg_rating / 5.0) * 70.0
    # Review count component (max 30) — logarithmic scaling
    if review_count == 0:
        count_score = 15  # neutral if unknown
    else:
        count_score = min(30, 15 * math.log10(review_count + 1))
    return max(0.0, min(100.0, rating_score + count_score))


def parse_vendor_score(trust_pilot_rating: float = 0, bbb_rating: str = "", has_warranty: bool = True) -> float:
    """
    Convert vendor trust signals to a 0-100 score.
    
    Args:
        trust_pilot_rating: Trustpilot score (0-5)
        bbb_rating: BBB grade (A+, A, A-, B+, etc.)
        has_warranty: Whether vendor offers warranty
        
    Returns:
        Score 0-100
    """
    score = 50.0  # baseline neutral
    
    if trust_pilot_rating > 0:
        score += (trust_pilot_rating / 5.0) * 30
    
    bbb_scores = {"A+": 20, "A": 15, "A-": 10, "B+": 5, "B": 0, "B-": -5, "C": -10, "F": -20}
    score += bbb_scores.get(bbb_rating.upper(), 0)
    
    if has_warranty:
        score += 10
    
    return max(0.0, min(100.0, score))


# ── Pretty-print helpers ────────────────────────────────────────────

def format_score_table(scores: list[ProductScore]) -> str:
    """
    Format a list of scored products as a human-readable table.
    """
    if not scores:
        return "No products scored."

    header = (
        f"{'Rank':<5} {'Product':<30} {'Vendor':<18} {'Score':>7}  "
        f"{'Price':>6} {'Quality':>7} {'Ship':>6} {'Trust':>6}"
    )
    sep = "─" * len(header)
    
    lines = [header, sep]
    for ps in scores:
        dim_map = {d.name: d.score for d in ps.dimensions}
        lines.append(
            f"{ps.rank_in_batch:<5} "
            f"{ps.product_name[:28]:<30} "
            f"{ps.vendor[:16]:<18} "
            f"{ps.total_weighted_score:>6.1f}  "
            f"{dim_map.get('price', 0):>5.0f} "
            f"{dim_map.get('quality', 0):>6.0f} "
            f"{dim_map.get('shipping_speed', 0):>5.0f} "
            f"{dim_map.get('vendor_reputation', 0):>5.0f}"
        )
    
    lines.append(sep)
    return "\n".join(lines)


def format_dimension_breakdown(ps: ProductScore) -> str:
    """
    Format a detailed breakdown for a single product.
    """
    lines = [
        f"  {ps.product_name} ({ps.vendor})",
        f"  Total Score: {ps.total_weighted_score:.1f}/100  "
        f"{'★ BEST' if ps.rank_in_batch == 1 else ''}",
    ]
    if ps.url:
        lines.append(f"  URL: {ps.url}")
    lines.append("")
    
    for d in ps.dimensions:
        bar_len = int(d.score / 5)  # 20 bars max
        bar = "█" * bar_len + "░" * (20 - bar_len)
        label = DIM_LABELS.get(d.name, d.name)
        lines.append(f"  {label:<28} [{bar}] {d.score:>5.1f} ({d.weighted_score:.1f})")
        if d.rationale:
            lines.append(f"    → {d.rationale}")
    
    return "\n".join(lines)
