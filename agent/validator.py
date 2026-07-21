from __future__ import annotations
from dataclasses import dataclass
from statistics import mean, stdev
from scorer import ProductScore, get_preset_labels

DEFAULT_SCORE = 50


@dataclass
class ValidationFlag:
    severity: str  # "info" | "warning" | "error"
    product_vendor: str
    field: str
    message: str
    suggestion: str = ""
    source: str = "rule"  # "rule" | "ai"


@dataclass
class ValidationResult:
    product_name: str
    vendor: str
    flags: list[ValidationFlag]
    adjusted_confidence: float
    override_score: float | None = None
    missing_data_ratio: float = 0.0


PENALTY_MAP = {
    "error": 0.15,
    "warning": 0.08,
    "info": 0.03,
}


def _dim_value(dim_map: dict, *keys: str) -> float | None:
    for k in keys:
        v = dim_map.get(k)
        if v is not None:
            return v
    return None


def _detect_price_quality_mismatch(ps: ProductScore, dim_map: dict) -> list[ValidationFlag]:
    flags = []
    price = _dim_value(dim_map, "price", "unit_price")
    quality = dim_map.get("quality")
    if price is not None and quality is not None:
        diff = price - quality
        if diff > 40:
            flags.append(ValidationFlag(
                severity="warning",
                product_vendor=f"{ps.product_name} ({ps.vendor})",
                field="price",
                message=f"Price score ({price:.0f}) far exceeds quality score ({quality:.0f}) — price advantage may be misleading",
                suggestion="Check if quality data is missing or if the product has known defects",
            ))
        elif diff < -40:
            flags.append(ValidationFlag(
                severity="warning",
                product_vendor=f"{ps.product_name} ({ps.vendor})",
                field="quality",
                message=f"Quality score ({quality:.0f}) far exceeds price score ({price:.0f}) — premium pricing may not be justified",
                suggestion="Verify quality data sources and check if cheaper alternatives exist",
            ))
    return flags


def _detect_cross_dimension_mismatches(ps: ProductScore, dim_map: dict) -> list[ValidationFlag]:
    flags = []
    pairs = [
        ("quality", ("warranty_service", "warranty"), "quality", "warranty",
         "High quality ({a:.0f}) with low warranty ({b:.0f}) — warranty may be inadequate for premium item",
         "Check warranty terms for high-quality products"),
        ("vendor_reputation", ("warranty_service", "warranty"), "vendor reputation", "warranty",
         "Strong vendor reputation ({a:.0f}) but weak warranty ({b:.0f}) — reputation may not cover product risk",
         "Verify if warranty is truly absent or just not detected"),
        ("quality", ("vendor_reputation", "supplier_trust"), "quality", "vendor trust",
         "High quality ({a:.0f}) but low vendor trust ({b:.0f}) — verify the seller is authorized",
         "Cross-check the vendor against authorized reseller lists"),
        ("price", ("logistics", "shipping_speed"), "price", "logistics",
         "Low price ({a:.0f}) but poor logistics ({b:.0f}) — check for hidden shipping costs",
         "Verify total landed cost including shipping"),
    ]
    for dim_a, dim_b_keys, label_a, label_b, msg_fmt, suggestion_fmt in pairs:
        a = dim_map.get(dim_a)
        b = _dim_value(dim_map, *dim_b_keys)
        if a is not None and b is not None:
            diff = a - b
            if abs(diff) > 40:
                flags.append(ValidationFlag(
                    severity="info" if abs(diff) < 50 else "warning",
                    product_vendor=f"{ps.product_name} ({ps.vendor})",
                    field=dim_a,
                    message=msg_fmt.format(a=a, b=b),
                    suggestion=suggestion_fmt,
                ))
    return flags


def _detect_outliers(scored: list[ProductScore], all_dim_maps: list[dict]) -> dict[str, list[ValidationFlag]]:
    dims_of_interest = ["price", "unit_price", "quality", "vendor_reputation", "supplier_trust"]
    raw_values: dict[str, list[float]] = {d: [] for d in dims_of_interest}
    for dm in all_dim_maps:
        for d in dims_of_interest:
            v = dm.get(d)
            if v is not None and v != DEFAULT_SCORE:
                raw_values[d].append(v)

    flags_by_product: dict[str, list[ValidationFlag]] = {}
    for ps, dm in zip(scored, all_dim_maps):
        for d in dims_of_interest:
            vals = raw_values.get(d, [])
            if len(vals) < 3:
                continue
            v = dm.get(d)
            if v is None or v == DEFAULT_SCORE:
                continue
            try:
                mu = mean(vals)
                sigma = stdev(vals)
            except Exception:
                continue
            if sigma == 0:
                continue
            z = (v - mu) / sigma
            if abs(z) > 2.5:
                label_d = d.replace("_", " ").title()
                key = f"{ps.product_name}::{ps.vendor}"
                flags_by_product.setdefault(key, []).append(ValidationFlag(
                    severity="warning" if abs(z) > 3 else "info",
                    product_vendor=f"{ps.product_name} ({ps.vendor})",
                    field=d,
                    message=f"{label_d} score ({v:.0f}) is {abs(z):.1f}σ {'above' if z > 0 else 'below'} batch mean ({mu:.0f}) — statistical outlier",
                    suggestion=f"Verify the {label_d.lower()} data; it deviates significantly from alternatives",
                ))
    return flags_by_product


def _detect_data_quality_inconsistency(ps: ProductScore, dim_map: dict) -> list[ValidationFlag]:
    flags = []
    for d in ps.dimensions:
        has_data = ps.data_quality.get(d.name, False)
        if has_data and d.score == DEFAULT_SCORE:
            flags.append(ValidationFlag(
                severity="warning",
                product_vendor=f"{ps.product_name} ({ps.vendor})",
                field=d.name,
                message=f"'{d.name}' flagged as data-backed but scored exactly {DEFAULT_SCORE} — data may not be meaningful",
                suggestion="Review raw data for this dimension — the extraction may have found weak signals",
            ))
    return flags


def _detect_default_scores(ps: ProductScore) -> list[ValidationFlag]:
    flags = []
    defaults = [d for d in ps.dimensions if d.score == DEFAULT_SCORE and d.weight > 0]
    if len(defaults) >= len([d for d in ps.dimensions if d.weight > 0]) // 2:
        names = ", ".join(d.name for d in defaults)
        flags.append(ValidationFlag(
            severity="info",
            product_vendor=f"{ps.product_name} ({ps.vendor})",
            field="multiple",
            message=f"{len(defaults)} of {len([d for d in ps.dimensions if d.weight > 0])} weighted dimensions at default score ({DEFAULT_SCORE}) — significant data gap",
            suggestion=f"Consider gathering more data for: {names}",
        ))
    return flags


def _detect_duplicate_products(scored: list[ProductScore]) -> list[ValidationFlag]:
    flags = []
    seen = {}
    for ps in scored:
        key = (ps.vendor.lower(), ps.product_name.lower())
        prev = seen.get(key)
        if prev:
            flags.append(ValidationFlag(
                severity="warning",
                product_vendor=prev.vendor,
                field="product_name",
                message=f"Duplicate product from {prev.vendor}: '{prev.product_name}'",
                suggestion="Merge or deduplicate — same product scored twice",
            ))
        else:
            seen[key] = ps
    return flags


def _detect_same_product_vendors(scored: list[ProductScore]) -> list[ValidationFlag]:
    flags = []
    groups: dict[str, list[ProductScore]] = {}
    for ps in scored:
        short = ps.product_name.lower().split("(")[0].strip().rstrip(",").rstrip("-").strip()
        short = " ".join(short.split()[:5])
        groups.setdefault(short, []).append(ps)
    for name, group in groups.items():
        if len(group) < 2:
            continue
        price_scores = []
        for ps in group:
            for d in ps.dimensions:
                if d.name in ("price", "unit_price") and d.weight > 0:
                    price_scores.append((ps.vendor, d.score))
        if len(price_scores) < 2:
            continue
        prices = [p[1] for p in price_scores]
        if max(prices) - min(prices) > 50:
            vendors_str = ", ".join(f"{p[0]} ({p[1]:.0f})" for p in price_scores)
            flags.append(ValidationFlag(
                severity="info",
                product_vendor=group[0].vendor,
                field="price",
                message=f"Same product '{name}' from multiple vendors shows large price score spread: {vendors_str}",
                suggestion="Verify pricing data — large variance may indicate different SKUs or data errors",
            ))
    return flags


def _detect_winner_fragility(scored: list[ProductScore]) -> list[ValidationFlag]:
    flags = []
    if len(scored) < 2:
        return flags
    gap = scored[0].total_weighted_score - scored[1].total_weighted_score
    if gap < 5:
        flags.append(ValidationFlag(
            severity="warning" if gap < 3 else "info",
            product_vendor=f"{scored[0].product_name} ({scored[0].vendor})",
            field="rank",
            message=f"Tight race: #{1} ({scored[0].vendor}: {scored[0].total_weighted_score:.0f}) vs #{2} ({scored[1].vendor}: {scored[1].total_weighted_score:.0f}) — gap of only {gap:.1f} pts",
            suggestion="Consider the alternatives carefully; small weight changes could flip the ranking",
        ))
    return flags


def _detect_vendor_consistency(scored: list[ProductScore]) -> list[ValidationFlag]:
    flags = []
    vendor_scores: dict[str, list[float]] = {}
    for ps in scored:
        vendor_scores.setdefault(ps.vendor, []).append(ps.total_weighted_score)
    for vendor, scores in vendor_scores.items():
        if len(scores) > 1 and max(scores) - min(scores) > 30:
            flags.append(ValidationFlag(
                severity="info",
                product_vendor=vendor,
                field="score",
                message=f"Vendor '{vendor}' shows {len(scores)} products with score spread of {max(scores) - min(scores):.0f} pts",
                suggestion="Check if these are genuinely different products or misattributed",
            ))
    return flags


def _detect_low_confidence_winners(scored: list[ProductScore]) -> list[ValidationFlag]:
    flags = []
    if not scored:
        return flags
    if scored[0].confidence < 0.6:
        flags.append(ValidationFlag(
            severity="error",
            product_vendor=f"{scored[0].product_name} ({scored[0].vendor})",
            field="confidence",
            message=f"Top-ranked product has low confidence ({scored[0].confidence:.0%}) — findings may not be reliable",
            suggestion="Consider gathering more data before making a decision",
        ))
    if len(scored) > 1 and scored[1].confidence < 0.6:
        flags.append(ValidationFlag(
            severity="warning",
            product_vendor=f"{scored[1].product_name} ({scored[1].vendor})",
            field="confidence",
            message=f"Runner-up has low confidence ({scored[1].confidence:.0%})",
            suggestion="Second opinion recommended before choosing runner-up",
        ))
    return flags


def _compute_missing_data_ratio(ps: ProductScore) -> float:
    weighted = [d for d in ps.dimensions if d.weight > 0]
    if not weighted:
        return 0.0
    missing = sum(1 for d in weighted if not ps.data_quality.get(d.name, False))
    return missing / len(weighted)


def _compute_confidence_penalty(flags: list[ValidationFlag], missing_data_ratio: float) -> float:
    penalty = 0.0
    for f in flags:
        penalty += PENALTY_MAP.get(f.severity, 0.03)
    penalty += missing_data_ratio * 0.15
    return min(penalty, 0.5)


def validate_batch(
    scored: list[ProductScore],
    preset: str = "consumer",
) -> dict[str, ValidationResult]:
    labels = get_preset_labels(preset)
    all_dim_maps = [{d.name: d.score for d in ps.dimensions} for ps in scored]
    outlier_map = _detect_outliers(scored, all_dim_maps)

    results = {}
    global_flags = []

    for ps in scored:
        dim_map = {d.name: d.score for d in ps.dimensions}
        key = f"{ps.product_name}::{ps.vendor}"

        flags = []
        flags.extend(_detect_price_quality_mismatch(ps, dim_map))
        flags.extend(_detect_cross_dimension_mismatches(ps, dim_map))
        flags.extend(_detect_data_quality_inconsistency(ps, dim_map))
        flags.extend(_detect_default_scores(ps))
        flags.extend(outlier_map.get(key, []))

        missing_ratio = _compute_missing_data_ratio(ps)
        penalty = _compute_confidence_penalty(flags, missing_ratio)
        adjusted_conf = max(0.25, round(ps.confidence - penalty, 2))

        results[key] = ValidationResult(
            product_name=ps.product_name,
            vendor=ps.vendor,
            flags=flags,
            adjusted_confidence=adjusted_conf,
            missing_data_ratio=round(missing_ratio, 2),
        )

    global_flags.extend(_detect_duplicate_products(scored))
    global_flags.extend(_detect_same_product_vendors(scored))
    global_flags.extend(_detect_vendor_consistency(scored))
    global_flags.extend(_detect_low_confidence_winners(scored))
    global_flags.extend(_detect_winner_fragility(scored))

    results["__global__"] = ValidationResult(
        product_name="__global__",
        vendor="__global__",
        flags=global_flags,
        adjusted_confidence=1.0,
    )

    return results


def apply_validation(
    scored: list[ProductScore],
    validation: dict[str, ValidationResult],
) -> list[ProductScore]:
    adjusted = []
    for ps in scored:
        key = f"{ps.product_name}::{ps.vendor}"
        vr = validation.get(key)
        if vr:
            ratio = vr.missing_data_ratio
            ps.confidence = vr.adjusted_confidence
            multiplier = 1.0 - (ratio * 0.15)
            ps.total_weighted_score = round(ps.total_weighted_score * multiplier * vr.adjusted_confidence, 2)
            ps.metadata["validation_flags"] = [
                {"severity": f.severity, "message": f.message, "field": f.field, "source": f.source}
                for f in vr.flags
            ]
        adjusted.append(ps)

    global_vr = validation.get("__global__")
    if global_vr and global_vr.flags:
        adjusted[0].metadata["global_validation"] = [
            {"severity": f.severity, "message": f.message, "field": f.field, "source": f.source}
            for f in global_vr.flags
        ]

    adjusted.sort(key=lambda x: x.total_weighted_score, reverse=True)
    for i, ps in enumerate(adjusted, 1):
        ps.rank_in_batch = i

    return adjusted


def print_validation_summary(validation: dict[str, ValidationResult]) -> None:
    total_errors = 0
    total_warnings = 0
    total_infos = 0
    ai_errors = 0
    ai_warnings = 0
    ai_infos = 0

    for key, vr in validation.items():
        if key == "__global__":
            continue
        for f in vr.flags:
            if f.source == "ai":
                if f.severity == "error":
                    ai_errors += 1
                elif f.severity == "warning":
                    ai_warnings += 1
                elif f.severity == "info":
                    ai_infos += 1
            else:
                if f.severity == "error":
                    total_errors += 1
                elif f.severity == "warning":
                    total_warnings += 1
                elif f.severity == "info":
                    total_infos += 1

    global_vr = validation.get("__global__")
    if global_vr:
        for f in global_vr.flags:
            if f.source == "ai":
                if f.severity == "error":
                    ai_errors += 1
                elif f.severity == "warning":
                    ai_warnings += 1
                elif f.severity == "info":
                    ai_infos += 1
            else:
                if f.severity == "error":
                    total_errors += 1
                elif f.severity == "warning":
                    total_warnings += 1
                elif f.severity == "info":
                    total_infos += 1

    parts = [f"  🛡️  Validation: {total_infos} info, {total_warnings} warnings, {total_errors} errors"]
    if ai_infos or ai_warnings or ai_errors:
        parts.append(f"  🤖 AI Judge: {ai_infos} info, {ai_warnings} warnings, {ai_errors} errors")
    print("\n".join(parts))

    per_product = {k: v for k, v in validation.items() if k != "__global__"}
    for key, vr in sorted(per_product.items(), key=lambda x: len(x[1].flags), reverse=True):
        if not vr.flags:
            continue
        ai_count = sum(1 for f in vr.flags if f.source == "ai")
        dq_note = f" (missing data: {vr.missing_data_ratio:.0%})" if vr.missing_data_ratio > 0.3 else ""
        badge = f" [AI: {ai_count}]" if ai_count else ""
        print(f"     {vr.product_name} ({vr.vendor}): {len(vr.flags)} flag(s){badge}{dq_note}")
        for f in vr.flags:
            icon = {"info": "  ℹ️", "warning": "  ⚠️", "error": "  ❌"}[f.severity]
            tag = " [AI]" if f.source == "ai" else ""
            print(f"     {icon}{tag} {f.message}")

    if global_vr and global_vr.flags:
        ai_count = sum(1 for f in global_vr.flags if f.source == "ai")
        badge = f" [AI: {ai_count}]" if ai_count else ""
        print(f"     (cross-product{badge})")
        for f in global_vr.flags:
            icon = {"info": "  ℹ️", "warning": "  ⚠️", "error": "  ❌"}[f.severity]
            tag = " [AI]" if f.source == "ai" else ""
            print(f"     {icon}{tag} {f.message}")
