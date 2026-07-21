"""
8-Dimension Rubric Scorer for Sparrow product comparisons.

Scores product alternatives across 8 dimensions (0-100 each),
computes a weighted total, and returns a structured score dict.

Supports multiple rubric presets (Consumer, Business) with
different dimension definitions, labels, and weights.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Rubric presets ─────────────────────────────────────────────

RUBRIC_PRESETS = {
    "consumer": {
        "label": "Consumer",
        "description": "Balanced scoring for personal purchasing decisions. Weights price and quality equally with moderate emphasis on shipping speed and vendor trust.",
        "dimensions": [
            ("price",              {"label": "Price",              "weight": 0.25}),
            ("quality",            {"label": "Quality / Reliability", "weight": 0.20}),
            ("shipping_speed",     {"label": "Shipping Speed",     "weight": 0.15}),
            ("vendor_reputation",  {"label": "Vendor Reputation",  "weight": 0.15}),
            ("warranty_service",   {"label": "Warranty / Service", "weight": 0.10}),
            ("sustainability",     {"label": "Sustainability",     "weight": 0.05}),
            ("secondhand_condition", {"label": "Secondhand Condition", "weight": 0.05}),
            ("preference_alignment", {"label": "Preference Alignment", "weight": 0.05}),
        ],
    },
    "business": {
        "label": "Business / CFO",
        "description": "Total cost of ownership scoring for business purchasing. Merges shipping cost dimensions into a single logistics score — optimized for procurement decisions.",
        "dimensions": [
            ("unit_price",         {"label": "Unit Price",         "weight": 0.25}),
            ("quality",            {"label": "Quality Score",      "weight": 0.20}),
            ("supplier_trust",     {"label": "Supplier Trust",     "weight": 0.15}),
            ("compatibility_risk", {"label": "Compatibility Risk", "weight": 0.13}),
            ("logistics",          {"label": "Logistics Score",    "weight": 0.15}),
            ("speed_reliability",  {"label": "Speed & Reliability","weight": 0.10}),
            ("sustainability",     {"label": "Sustainability",     "weight": 0.02}),
        ],
    },
    "it_procurement": {
        "label": "IT Procurement",
        "description": "Enterprise IT purchasing with emphasis on compatibility risk, warranty/service, and supplier trust. Designed for office technology (toner, printers, peripherals).",
        "dimensions": [
            ("unit_price",          {"label": "Unit Price",          "weight": 0.20}),
            ("quality",             {"label": "Quality / Reliability","weight": 0.15}),
            ("compatibility_risk",  {"label": "Compatibility Risk",  "weight": 0.20}),
            ("supplier_trust",      {"label": "Supplier Trust",      "weight": 0.12}),
            ("warranty_service",    {"label": "Warranty / Service",  "weight": 0.15}),
            ("logistics",           {"label": "Logistics Score",     "weight": 0.10}),
            ("speed_reliability",   {"label": "Speed & Reliability", "weight": 0.05}),
            ("sustainability",      {"label": "Sustainability",      "weight": 0.03}),
        ],
    },
    "freight_forwarder": {
        "label": "Freight Forwarder",
        "description": "Logistics-centric scoring for freight/shipping decisions. Heavy weight on landed cost, logistics speed, and supplier trust. Minimal sustainability emphasis.",
        "dimensions": [
            ("logistics",          {"label": "Logistics Score",     "weight": 0.30}),
            ("unit_price",         {"label": "Unit Price / Cost",   "weight": 0.20}),
            ("quality",            {"label": "Quality Score",       "weight": 0.10}),
            ("supplier_trust",     {"label": "Supplier Trust",      "weight": 0.15}),
            ("speed_reliability",  {"label": "Speed & Reliability", "weight": 0.15}),
            ("compatibility_risk", {"label": "Compatibility Risk",  "weight": 0.05}),
            ("sustainability",     {"label": "Sustainability",      "weight": 0.05}),
        ],
    },
}


def get_preset(preset: str) -> dict:
    if preset not in RUBRIC_PRESETS:
        available = list(RUBRIC_PRESETS.keys())
        raise ValueError(f"Unknown rubric preset '{preset}'. Available: {available}")
    return RUBRIC_PRESETS[preset]


def get_preset_dimensions(preset: str) -> list[tuple[str, dict]]:
    return get_preset(preset)["dimensions"]


def get_preset_weights(preset: str) -> dict[str, float]:
    return {k: v["weight"] for k, v in get_preset_dimensions(preset)}


def get_preset_labels(preset: str) -> dict[str, str]:
    return {k: v["label"] for k, v in get_preset_dimensions(preset)}


def get_preset_dim_keys(preset: str) -> list[str]:
    return [k for k, _ in get_preset_dimensions(preset)]


# ── Backward compatibility aliases (Consumer preset) ──────────

DIMENSIONS = get_preset_dim_keys("consumer")
DEFAULT_WEIGHTS = get_preset_weights("consumer")
DIM_LABELS = get_preset_labels("consumer")


# ── Data structures ───────────────────────────────────────────

@dataclass
class DimensionScore:
    name: str
    score: float
    weight: float
    weighted_score: float
    rationale: str = ""


@dataclass
class ProductScore:
    product_name: str
    vendor: str
    url: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    total_weighted_score: float = 0.0
    rank_in_batch: int = 1
    is_secondhand: bool = False
    metadata: dict = field(default_factory=dict)
    data_quality: dict[str, bool] = field(default_factory=dict)
    confidence: float = 1.0

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
            "confidence": round(self.confidence, 2),
        }


# ── Core scorer ──────────────────────────────────────────────

def score_product(
    product_name: str,
    vendor: str,
    url: str = "",
    scores: Optional[dict[str, float]] = None,
    weights: Optional[dict[str, float]] = None,
    preset: Optional[str] = None,
    is_secondhand: bool = False,
    secondhand_grade: Optional[str] = None,
    rationale: Optional[dict[str, str]] = None,
    metadata: Optional[dict] = None,
    data_quality: Optional[dict[str, bool]] = None,
    reference_scores: Optional[dict[str, float]] = None,
) -> ProductScore:
    weights = weights or DEFAULT_WEIGHTS.copy() if preset is None else get_preset_weights(preset)
    dim_keys = list(weights.keys())
    scores = scores or {}
    rationale = rationale or {}
    metadata = metadata or {}
    data_quality = data_quality or {}

    if reference_scores:
        for dim in dim_keys:
            ref = reference_scores.get(dim)
            if ref is not None:
                if dim not in scores:
                    scores[dim] = ref
                ref_val_delta = scores[dim] - ref
                if scores[dim] >= ref:
                    scores[dim] = min(100, 50 + ref_val_delta * 1.0)
                else:
                    scores[dim] = max(0, 50 + ref_val_delta * 1.0)

    if is_secondhand and secondhand_grade:
        grade_multipliers = {
            "excellent": 0.9,
            "good": 0.7,
            "fair": 0.5,
            "acceptable": 0.3,
        }
        mult = grade_multipliers.get(secondhand_grade.lower(), 0.5)
        sk = "secondhand_condition"
        if sk in weights and weights[sk] > 0:
            scores[sk] = min(100, scores.get(sk, 50) * mult)

    dimensions = []
    total_weighted = 0.0
    total_weight = 0.0

    for dim in dim_keys:
        dim_score = scores.get(dim, 50.0)
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

    if total_weight > 0:
        total_weighted /= total_weight

    if data_quality and dim_keys:
        found = sum(1 for d in dim_keys if data_quality.get(d, False))
        confidence = 0.5 + 0.5 * (found / len(dim_keys))
    else:
        confidence = 1.0

    return ProductScore(
        product_name=product_name,
        vendor=vendor,
        url=url,
        dimensions=dimensions,
        total_weighted_score=round(total_weighted * confidence, 2),
        is_secondhand=is_secondhand,
        metadata=metadata,
        data_quality=data_quality,
        confidence=round(confidence, 2),
    )


def score_batch(
    products: list[dict],
    weights: Optional[dict] = None,
    preset: Optional[str] = None,
) -> list[ProductScore]:
    scored = []
    for p in products:
        ps = score_product(
            product_name=p["product_name"],
            vendor=p["vendor"],
            url=p.get("url", ""),
            scores=p.get("scores", {}),
            weights=weights,
            preset=preset,
            is_secondhand=p.get("is_secondhand", False),
            secondhand_grade=p.get("secondhand_grade"),
            rationale=p.get("rationale", {}),
            metadata=p.get("metadata", {}),
            data_quality=p.get("data_quality"),
            reference_scores=p.get("reference_scores"),
        )
        scored.append(ps)

    scored.sort(key=lambda x: x.total_weighted_score, reverse=True)
    for i, ps in enumerate(scored, 1):
        ps.rank_in_batch = i

    return scored


# ── Convenience: parse raw product data into scores ──────────

def parse_price_score(raw_price: float, price_range: tuple[float, float]) -> float:
    lo, hi = price_range
    if lo == hi:
        return 100.0
    score = 100.0 * (1.0 - (raw_price - lo) / (hi - lo))
    return max(0.0, min(100.0, score))


def parse_shipping_score(days: int, free_shipping: bool = False) -> float:
    score = 100.0 - (days * 8)
    if free_shipping:
        score += 15
    return max(0.0, min(100.0, score))


def parse_quality_score(avg_rating: float, review_count: int = 0) -> float:
    rating_score = (avg_rating / 5.0) * 70.0
    if review_count == 0:
        count_score = 15
    else:
        count_score = min(30, 15 * math.log10(review_count + 1))
    return max(0.0, min(100.0, rating_score + count_score))


def parse_vendor_score(
    trust_pilot_rating: float = 0,
    bbb_rating: str = "",
    has_warranty: bool = False,
    sentiment_score: float | None = None,
    has_return_policy: bool = False,
) -> float:
    score = 50.0
    if trust_pilot_rating > 0:
        score += (trust_pilot_rating / 5.0) * 30
    if sentiment_score is not None:
        score = score * 0.4 + sentiment_score * 0.6
    bbb_scores = {"A+": 20, "A": 15, "A-": 10, "B+": 5, "B": 0, "B-": -5, "C": -10, "F": -20}
    score += bbb_scores.get(bbb_rating.upper(), 0)
    if has_warranty:
        score += 10
    if has_return_policy:
        score += 10
    return max(0.0, min(100.0, score))


# ── Pretty-print helpers ─────────────────────────────────────

def _labels_for_preset(preset: Optional[str]) -> dict[str, str]:
    return get_preset_labels(preset) if preset else DIM_LABELS


def format_score_table(scores: list[ProductScore], preset: Optional[str] = None) -> str:
    if not scores:
        return "No products scored."

    labels = _labels_for_preset(preset)
    dim_keys = list(labels.keys())

    header_parts = [f"{'Rank':<5} {'Product':<30} {'Vendor':<18} {'Score':>7}"]
    for k in dim_keys[:4]:
        short = labels[k][:6]
        header_parts.append(f" {short:>6}")
    header = " ".join(header_parts)
    sep = "─" * len(header)

    lines = [header, sep]
    for ps in scores:
        dim_map = {d.name: d.score for d in ps.dimensions}
        row = f"{ps.rank_in_batch:<5} {ps.product_name[:28]:<30} {ps.vendor[:16]:<18} {ps.total_weighted_score:>6.1f}"
        for k in dim_keys[:4]:
            row += f" {dim_map.get(k, 0):>5.0f}"
        lines.append(row)

    lines.append(sep)
    return "\n".join(lines)


def format_dimension_breakdown(ps: ProductScore, preset: Optional[str] = None) -> str:
    labels = _labels_for_preset(preset)
    lines = [
        f"  {ps.product_name} ({ps.vendor})",
        f"  Total Score: {ps.total_weighted_score:.1f}/100  "
        f"{'★ BEST' if ps.rank_in_batch == 1 else ''}",
    ]
    if ps.url:
        lines.append(f"  URL: {ps.url}")
    lines.append("")

    for d in ps.dimensions:
        if d.weight == 0:
            continue
        bar_len = int(d.score / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        label = labels.get(d.name, d.name)
        lines.append(f"  {label:<28} [{bar}] {d.score:>5.1f} ({d.weighted_score:.1f})")
        if d.rationale:
            lines.append(f"    → {d.rationale}")

    return "\n".join(lines)
