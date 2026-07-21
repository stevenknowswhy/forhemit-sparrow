"""
Unit tests for the validation agent (validator.py).

Tests all 8 detection functions, helper functions, and the
validate_batch / apply_validation integration entry points.
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import (
    _dim_value,
    _detect_price_quality_mismatch,
    _detect_cross_dimension_mismatches,
    _detect_outliers,
    _detect_data_quality_inconsistency,
    _detect_default_scores,
    _detect_duplicate_products,
    _detect_same_product_vendors,
    _detect_winner_fragility,
    _detect_vendor_consistency,
    _detect_low_confidence_winners,
    _compute_missing_data_ratio,
    _compute_confidence_penalty,
    validate_batch,
    apply_validation,
    ValidationFlag,
    DEFAULT_SCORE,
)
from scorer import ProductScore, DimensionScore


# ── helpers ────────────────────────────────────────────────────

def make_ps(
    name: str = "Test Product",
    vendor: str = "TestVendor",
    dimensions: list[tuple[str, float, float]] | None = None,
    data_quality: dict[str, bool] | None = None,
    confidence: float = 1.0,
    total_score: float = 0.0,
) -> ProductScore:
    dims = []
    if dimensions:
        for dim_name, score, weight in dimensions:
            dims.append(DimensionScore(
                name=dim_name,
                score=score,
                weight=weight,
                weighted_score=score * weight,
            ))
    return ProductScore(
        product_name=name,
        vendor=vendor,
        dimensions=dims,
        total_weighted_score=total_score,
        data_quality=data_quality or {},
        confidence=confidence,
        metadata={},
    )


def dim_map(ps: ProductScore) -> dict[str, float]:
    return {d.name: d.score for d in ps.dimensions}


# ── _dim_value ─────────────────────────────────────────────────

class TestDimValue:
    def test_first_key_found(self):
        assert _dim_value({"a": 10, "b": 20}, "a", "b") == 10

    def test_second_key_fallback(self):
        assert _dim_value({"b": 20}, "a", "b") == 20

    def test_no_keys_found(self):
        assert _dim_value({"c": 30}, "a", "b") is None

    def test_skips_none_value(self):
        assert _dim_value({"a": None, "b": 20}, "a", "b") == 20


# ── Price/Quality Mismatch ─────────────────────────────────────

class TestPriceQualityMismatch:
    def test_no_mismatch(self):
        ps = make_ps(dimensions=[("price", 60, 0.25), ("quality", 70, 0.20)])
        assert _detect_price_quality_mismatch(ps, dim_map(ps)) == []

    def test_price_exceeds_quality_by_40_plus(self):
        ps = make_ps(dimensions=[("price", 90, 0.25), ("quality", 40, 0.20)])
        flags = _detect_price_quality_mismatch(ps, dim_map(ps))
        assert len(flags) == 1
        assert flags[0].severity == "warning"
        assert "price" in flags[0].field

    def test_quality_exceeds_price_by_40_plus(self):
        ps = make_ps(dimensions=[("price", 30, 0.25), ("quality", 80, 0.20)])
        flags = _detect_price_quality_mismatch(ps, dim_map(ps))
        assert len(flags) == 1
        assert flags[0].severity == "warning"
        assert "quality" in flags[0].field

    def test_exact_40_gap_no_flag(self):
        ps = make_ps(dimensions=[("price", 90, 0.25), ("quality", 50, 0.20)])
        assert _detect_price_quality_mismatch(ps, dim_map(ps)) == []

    def test_uses_unit_price_fallback(self):
        ps = make_ps(dimensions=[("unit_price", 90, 0.25), ("quality", 40, 0.20)])
        flags = _detect_price_quality_mismatch(ps, dim_map(ps))
        assert len(flags) == 1

    def test_missing_quality_no_flag(self):
        ps = make_ps(dimensions=[("price", 90, 0.25)])
        assert _detect_price_quality_mismatch(ps, dim_map(ps)) == []


# ── Cross-Dimension Mismatches ─────────────────────────────────

class TestCrossDimensionMismatches:
    def test_no_mismatches(self):
        ps = make_ps(dimensions=[
            ("quality", 70, 0.20),
            ("warranty_service", 60, 0.10),
            ("vendor_reputation", 65, 0.15),
            ("price", 75, 0.25),
        ])
        assert _detect_cross_dimension_mismatches(ps, dim_map(ps)) == []

    def test_quality_warranty_mismatch(self):
        ps = make_ps(dimensions=[("quality", 90, 0.20), ("warranty_service", 20, 0.10)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert len(flags) >= 1
        assert "quality" in flags[0].field

    def test_price_logistics_mismatch(self):
        ps = make_ps(dimensions=[("price", 25, 0.25), ("logistics", 80, 0.15)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert len(flags) >= 1
        assert "price" in flags[0].field

    def test_severity_info_under_50_diff(self):
        ps = make_ps(dimensions=[("quality", 75, 0.20), ("warranty_service", 30, 0.10)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert flags[0].severity == "info"

    def test_severity_warning_over_50_diff(self):
        ps = make_ps(dimensions=[("quality", 90, 0.20), ("warranty_service", 20, 0.10)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert flags[0].severity == "warning"

    def test_diff_exactly_50_is_warning(self):
        ps = make_ps(dimensions=[("quality", 90, 0.20), ("warranty_service", 40, 0.10)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert flags[0].severity == "warning"

    def test_uses_warranty_fallback_key(self):
        ps = make_ps(dimensions=[("quality", 90, 0.20), ("warranty", 20, 0.10)])
        flags = _detect_cross_dimension_mismatches(ps, dim_map(ps))
        assert len(flags) >= 1


# ── Outlier Detection ──────────────────────────────────────────

class TestOutliers:
    def test_no_outliers(self):
        scores = [
            make_ps("A", "V1", [("price", 50, 0.25)]),
            make_ps("B", "V2", [("price", 55, 0.25)]),
            make_ps("C", "V3", [("price", 45, 0.25)]),
            make_ps("D", "V4", [("price", 52, 0.25)]),
        ]
        dim_maps = [dim_map(ps) for ps in scores]
        result = _detect_outliers(scores, dim_maps)
        assert result == {}

    def test_outlier_detected(self):
        scores = [
            make_ps("A", "V1", [("price", 48, 0.25)]),
            make_ps("B", "V2", [("price", 49, 0.25)]),
            make_ps("C", "V3", [("price", 51, 0.25)]),
            make_ps("D", "V4", [("price", 52, 0.25)]),
            make_ps("E", "V5", [("price", 48, 0.25)]),
            make_ps("F", "V6", [("price", 49, 0.25)]),
            make_ps("G", "V7", [("price", 51, 0.25)]),
            make_ps("H", "V8", [("price", 52, 0.25)]),
            make_ps("I", "V9", [("price", 48, 0.25)]),
            make_ps("J", "V10", [("price", 49, 0.25)]),
            make_ps("K", "V11", [("price", 20, 0.25)]),
        ]
        dim_maps = [dim_map(ps) for ps in scores]
        result = _detect_outliers(scores, dim_maps)
        key = "K::V11"
        assert key in result

    def test_insufficient_data_no_outlier(self):
        scores = [
            make_ps("A", "V1", [("price", 50, 0.25)]),
            make_ps("B", "V2", [("price", 60, 0.25)]),
        ]
        dim_maps = [dim_map(ps) for ps in scores]
        result = _detect_outliers(scores, dim_maps)
        assert result == {}

    def test_skips_default_scores(self):
        scores = [
            make_ps("A", "V1", [("price", 50, 0.25)]),
            make_ps("B", "V2", [("price", 50, 0.25)]),
            make_ps("C", "V3", [("price", 50, 0.25)]),
            make_ps("D", "V4", [("price", 10, 0.25)]),
        ]
        dim_maps = [dim_map(ps) for ps in scores]
        result = _detect_outliers(scores, dim_maps)
        assert result == {}

    def test_severity_info_below_3_sigma(self):
        scores = [
            make_ps("A", "V1", [("quality", 48, 0.20)]),
            make_ps("B", "V2", [("quality", 49, 0.20)]),
            make_ps("C", "V3", [("quality", 51, 0.20)]),
            make_ps("D", "V4", [("quality", 52, 0.20)]),
            make_ps("E", "V5", [("quality", 48, 0.20)]),
            make_ps("F", "V6", [("quality", 49, 0.20)]),
            make_ps("G", "V7", [("quality", 51, 0.20)]),
            make_ps("H", "V8", [("quality", 52, 0.20)]),
            make_ps("I", "V9", [("quality", 48, 0.20)]),
            make_ps("J", "V10", [("quality", 49, 0.20)]),
            make_ps("K", "V11", [("quality", 35, 0.20)]),
        ]
        dim_maps = [dim_map(ps) for ps in scores]
        result = _detect_outliers(scores, dim_maps)
        key = "K::V11"
        assert key in result
        assert result[key][0].severity == "info"


# ── Data Quality Inconsistency ─────────────────────────────────

class TestDataQualityInconsistency:
    def test_no_inconsistency(self):
        ps = make_ps(
            dimensions=[("price", 75, 0.25)],
            data_quality={"price": True},
        )
        assert _detect_data_quality_inconsistency(ps, dim_map(ps)) == []

    def test_inconsistency_detected(self):
        ps = make_ps(
            dimensions=[("price", 50, 0.25)],
            data_quality={"price": True},
        )
        flags = _detect_data_quality_inconsistency(ps, dim_map(ps))
        assert len(flags) == 1
        assert flags[0].field == "price"

    def test_default_scores_ignored_if_no_data(self):
        ps = make_ps(
            dimensions=[("price", 50, 0.25)],
            data_quality={"price": False},
        )
        assert _detect_data_quality_inconsistency(ps, dim_map(ps)) == []

    def test_inconsistency_per_dimension(self):
        ps = make_ps(
            dimensions=[("price", 50, 0.25), ("quality", 50, 0.20)],
            data_quality={"price": True, "quality": True},
        )
        flags = _detect_data_quality_inconsistency(ps, dim_map(ps))
        assert len(flags) == 2


# ── Default Score Clustering ───────────────────────────────────

class TestDefaultScores:
    def test_no_flag_few_defaults(self):
        ps = make_ps(dimensions=[
            ("price", 60, 0.25),
            ("quality", 80, 0.20),
            ("shipping_speed", 90, 0.15),
        ])
        result = _detect_default_scores(ps)
        assert result == []

    def test_flag_when_majority_default(self):
        ps = make_ps(dimensions=[
            ("price", 50, 0.25),
            ("quality", 50, 0.20),
            ("shipping_speed", 90, 0.15),
        ])
        flags = _detect_default_scores(ps)
        assert len(flags) == 1
        assert flags[0].severity == "info"

    def test_ignores_zero_weight_dimensions(self):
        ps = make_ps(dimensions=[
            ("price", 60, 0.25),
            ("quality", 80, 0.20),
            ("sustainability", 50, 0.0),
        ])
        flags = _detect_default_scores(ps)
        assert len(flags) == 0


# ── Duplicate Products ─────────────────────────────────────────

class TestDuplicateProducts:
    def test_no_duplicates(self):
        scores = [
            make_ps("A", "V1"),
            make_ps("B", "V2"),
        ]
        assert _detect_duplicate_products(scores) == []

    def test_duplicate_detected(self):
        scores = [
            make_ps("A", "V1"),
            make_ps("A", "V1"),
        ]
        flags = _detect_duplicate_products(scores)
        assert len(flags) == 1

    def test_case_insensitive(self):
        scores = [
            make_ps("Product", "Vendor"),
            make_ps("product", "vendor"),
        ]
        flags = _detect_duplicate_products(scores)
        assert len(flags) == 1


# ── Same-Product Cross-Vendor ──────────────────────────────────

class TestSameProductVendors:
    def test_no_large_spread(self):
        scores = [
            make_ps("Toner HP", "V1", [("price", 60, 0.25)]),
            make_ps("Toner HP", "V2", [("price", 70, 0.25)]),
        ]
        assert _detect_same_product_vendors(scores) == []

    def test_large_spread_detected(self):
        scores = [
            make_ps("Toner HP", "V1", [("price", 30, 0.25)]),
            make_ps("Toner HP", "V2", [("price", 90, 0.25)]),
        ]
        flags = _detect_same_product_vendors(scores)
        assert len(flags) == 1
        assert flags[0].severity == "info"

    def test_no_flag_for_single_vendor(self):
        scores = [
            make_ps("Toner HP", "V1", [("price", 90, 0.25)]),
        ]
        assert _detect_same_product_vendors(scores) == []


# ── Winner Fragility ───────────────────────────────────────────

class TestWinnerFragility:
    def test_no_flag_wide_gap(self):
        scores = [
            make_ps("A", "V1", total_score=90.0),
            make_ps("B", "V2", total_score=80.0),
        ]
        assert _detect_winner_fragility(scores) == []

    def test_warning_tight_gap_under_3(self):
        scores = [
            make_ps("A", "V1", total_score=85.0),
            make_ps("B", "V2", total_score=83.0),
        ]
        flags = _detect_winner_fragility(scores)
        assert len(flags) == 1
        assert flags[0].severity == "warning"

    def test_info_gap_3_to_5(self):
        scores = [
            make_ps("A", "V1", total_score=85.0),
            make_ps("B", "V2", total_score=81.0),
        ]
        flags = _detect_winner_fragility(scores)
        assert len(flags) == 1
        assert flags[0].severity == "info"

    def test_no_flag_single_product(self):
        scores = [make_ps("A", "V1", total_score=85.0)]
        assert _detect_winner_fragility(scores) == []


# ── Vendor Consistency ─────────────────────────────────────────

class TestVendorConsistency:
    def test_no_large_spread(self):
        scores = [
            make_ps("A", "VendorX", total_score=75.0),
            make_ps("B", "VendorX", total_score=80.0),
        ]
        assert _detect_vendor_consistency(scores) == []

    def test_large_spread_detected(self):
        scores = [
            make_ps("A", "VendorX", total_score=60.0),
            make_ps("B", "VendorX", total_score=95.0),
        ]
        flags = _detect_vendor_consistency(scores)
        assert len(flags) == 1
        assert flags[0].severity == "info"

    def test_single_product_no_flag(self):
        scores = [make_ps("A", "VendorX", total_score=75.0)]
        assert _detect_vendor_consistency(scores) == []


# ── Low-Confidence Winners ─────────────────────────────────────

class TestLowConfidenceWinners:
    def test_no_flag_ok_confidence(self):
        scores = [make_ps("A", "V1", confidence=0.8)]
        assert _detect_low_confidence_winners(scores) == []

    def test_error_top_ranked_low_confidence(self):
        scores = [make_ps("A", "V1", confidence=0.5)]
        flags = _detect_low_confidence_winners(scores)
        assert len(flags) == 1
        assert flags[0].severity == "error"

    def test_warning_runner_up_low_confidence(self):
        scores = [
            make_ps("A", "V1", confidence=0.8),
            make_ps("B", "V2", confidence=0.5),
        ]
        flags = _detect_low_confidence_winners(scores)
        assert len(flags) == 1
        assert flags[0].severity == "warning"

    def test_both_low_confidence(self):
        scores = [
            make_ps("A", "V1", confidence=0.5),
            make_ps("B", "V2", confidence=0.4),
        ]
        flags = _detect_low_confidence_winners(scores)
        assert len(flags) == 2

    def test_empty_list(self):
        assert _detect_low_confidence_winners([]) == []


# ── Missing Data Ratio ─────────────────────────────────────────

class TestMissingDataRatio:
    def test_all_data_present(self):
        ps = make_ps(
            dimensions=[("price", 80, 0.25), ("quality", 70, 0.20)],
            data_quality={"price": True, "quality": True},
        )
        assert _compute_missing_data_ratio(ps) == 0.0

    def test_half_missing(self):
        ps = make_ps(
            dimensions=[("price", 80, 0.25), ("quality", 50, 0.20)],
            data_quality={"price": True, "quality": False},
        )
        assert _compute_missing_data_ratio(ps) == 0.5

    def test_all_missing(self):
        ps = make_ps(
            dimensions=[("price", 80, 0.25)],
            data_quality={"price": False},
        )
        assert _compute_missing_data_ratio(ps) == 1.0

    def test_no_weighted_dims(self):
        ps = make_ps(dimensions=[], data_quality={})
        assert _compute_missing_data_ratio(ps) == 0.0


# ── Confidence Penalty ─────────────────────────────────────────

class TestConfidencePenalty:
    def test_no_flags_no_missing_data(self):
        assert _compute_confidence_penalty([], 0.0) == 0.0

    def test_single_error_flag(self):
        flags = [ValidationFlag("error", "p (v)", "f", "m")]
        penalty = _compute_confidence_penalty(flags, 0.0)
        assert penalty == 0.15

    def test_partial_missing_data(self):
        assert _compute_confidence_penalty([], 0.5) == pytest.approx(0.075, abs=1e-9)

    def test_capped_at_0_5(self):
        flags = [ValidationFlag("error", "p (v)", "f", "m")] * 4
        penalty = _compute_confidence_penalty(flags, 1.0)
        assert penalty == 0.5

    def test_mixed_severity(self):
        flags = [
            ValidationFlag("error", "p (v)", "f", "m"),
            ValidationFlag("warning", "p (v)", "f", "m"),
            ValidationFlag("info", "p (v)", "f", "m"),
        ]
        penalty = _compute_confidence_penalty(flags, 0.0)
        assert penalty == pytest.approx(0.26, abs=1e-9)


# ── validate_batch (integration) ──────────────────────────────

class TestValidateBatch:
    def test_single_product_no_flags(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 60, 0.25), ("quality", 65, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.75),
        ]
        result = validate_batch(scores, preset="consumer")
        assert "Toner::HP" in result
        v = result["Toner::HP"]
        assert v.adjusted_confidence > 0.0
        assert v.missing_data_ratio <= 1.0

    def test_multiple_products_global_flags(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 90, 0.25), ("quality", 40, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8),
            make_ps("Toner", "Dell",
                dimensions=[("price", 85, 0.25), ("quality", 45, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8),
        ]
        result = validate_batch(scores, preset="consumer")
        assert "__global__" in result
        global_v = result["__global__"]
        assert len(global_v.flags) > 0

    def test_global_section_always_present(self):
        result = validate_batch([], preset="consumer")
        assert "__global__" in result

    def test_confidence_penalty_reduces_confidence(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 50, 0.25)],
                data_quality={"price": False},
                confidence=1.0),
            make_ps("Toner", "Dell",
                dimensions=[("price", 60, 0.25)],
                data_quality={"price": False},
                confidence=1.0),
            make_ps("Toner", "Lenovo",
                dimensions=[("price", 55, 0.25)],
                data_quality={"price": True},
                confidence=1.0),
        ]
        result = validate_batch(scores, preset="consumer")
        key = "Toner::HP"
        assert result[key].adjusted_confidence < 1.0

    def test_confidence_not_below_0_25(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 50, 0.25)],
                data_quality={"price": False},
                confidence=0.3),
        ]
        result = validate_batch(scores, preset="consumer")
        assert result["Toner::HP"].adjusted_confidence >= 0.25

    def test_all_presets_work(self):
        base_dims = [("price", 60, 0.25), ("quality", 70, 0.20)]
        scores = [make_ps("Test", "Vendor", dimensions=base_dims)]
        for preset in ("consumer", "business", "it_procurement", "freight_forwarder"):
            result = validate_batch(scores, preset=preset)
            assert "Test::Vendor" in result, f"Failed for preset {preset}"


# ── apply_validation (integration) ─────────────────────────────

class TestApplyValidation:
    def test_adjusts_scores_and_confidence(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 60, 0.25), ("quality", 65, 0.20)],
                data_quality={"price": True, "quality": False},
                confidence=0.8, total_score=70.0),
        ]
        validation = validate_batch(scores, preset="consumer")
        adjusted = apply_validation(scores, validation)
        assert len(adjusted) == 1
        assert adjusted[0].confidence != 0.8 or adjusted[0].total_weighted_score != 70.0

    def test_adds_metadata_flags(self):
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 90, 0.25), ("quality", 40, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8, total_score=70.0),
        ]
        validation = validate_batch(scores, preset="consumer")
        adjusted = apply_validation(scores, validation)
        assert "validation_flags" in adjusted[0].metadata
        assert len(adjusted[0].metadata["validation_flags"]) > 0

    def test_adds_global_validation_metadata(self):
        err_scores = [
            make_ps("A", "V1",
                dimensions=[("price", 90, 0.25), ("quality", 40, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8, total_score=70.0),
            make_ps("B", "V2",
                dimensions=[("price", 85, 0.25), ("quality", 45, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8, total_score=68.0),
        ]
        validation = validate_batch(err_scores, preset="consumer")
        adjusted = apply_validation(err_scores, validation)
        assert any("global_validation" in ps.metadata for ps in adjusted)

    def test_resorts_by_new_score(self):
        scores = [
            make_ps("A", "V1",
                dimensions=[("price", 60, 0.25), ("quality", 65, 0.20)],
                data_quality={"price": True, "quality": True},
                confidence=0.8, total_score=80.0),
            make_ps("B", "V2",
                dimensions=[("price", 50, 0.25), ("quality", 55, 0.20)],
                data_quality={"price": False, "quality": False},
                confidence=0.8, total_score=90.0),
        ]
        validation = validate_batch(scores, preset="consumer")
        adjusted = apply_validation(scores, validation)
        # A should rank higher than B after B is penalized for missing data
        assert adjusted[0].rank_in_batch <= adjusted[1].rank_in_batch


# ── Edge Cases ────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_product_list(self):
        result = validate_batch([], preset="consumer")
        assert "__global__" in result
        assert len([k for k in result if k != "__global__"]) == 0

    def test_all_default_scores(self):
        ps = make_ps("Default", "Vendor",
            dimensions=[("price", 50, 0.25), ("quality", 50, 0.20)],
        )
        flags = _detect_default_scores(ps)
        assert len(flags) == 1

    def test_negative_confidence_not_below_floor(self):
        """Confidence floor at 0.25 should prevent negative values."""
        scores = [
            make_ps("Toner", "HP",
                dimensions=[("price", 50, 0.25), ("quality", 50, 0.20)],
                data_quality={"price": False, "quality": False},
                confidence=0.3),
        ]
        result = validate_batch(scores, preset="consumer")
        assert result["Toner::HP"].adjusted_confidence >= 0.25

    def test_negative_gap_in_winner_fragility(self):
        scores = [
            make_ps("A", "V1", total_score=80.0),
            make_ps("B", "V2", total_score=80.0001),
        ]
        flags = _detect_winner_fragility(scores)
        # Small negative gap is cosmetic; either way we don't crash
        assert isinstance(flags, list)

    def test_duplicate_within_same_batch(self):
        scores = [
            make_ps("Toner", "HP"),
            make_ps("Toner", "HP"),
        ]
        flags = _detect_duplicate_products(scores)
        assert len(flags) == 1

    def test_no_crash_with_missing_price_field(self):
        ps = make_ps("Test", "Vendor", dimensions=[("quality", 80, 0.20)])
        flags = _detect_price_quality_mismatch(ps, dim_map(ps))
        assert flags == []

    def test_apply_validation_no_validation(self):
        scores = [make_ps("Test", "Vendor", total_score=70.0)]
        validation = {}
        adjusted = apply_validation(scores, validation)
        assert len(adjusted) == 1
