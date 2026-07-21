"""
Unit tests for the AI judge agent (judge.py).

Tests flag parsing, cache behavior, LLM interaction, and threshold handling.
All LLM calls are mocked — no real API keys or network needed.
"""
from __future__ import annotations
import json
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import judge as judge_module
from judge import (
    _parse_flags,
    _build_product_prompt,
    _build_cross_prompt,
    _parse_cross_flags,
    _judge_cross_products,
    _cache_key,
    _load_cache,
    _save_cache,
    _judge_product,
    judge_batch,
    _make_client,
    _THRESHOLD_PROMPTS,
    _THRESHOLD_TEMPS,
    _CACHE_TTL,
)
from scorer import ProductScore, DimensionScore


def make_ps(
    name="Test Product",
    vendor="TestVendor",
    url="https://example.com/product",
    dimensions=None,
    confidence=1.0,
):
    dims = []
    if dimensions:
        for dim_name, score, weight in dimensions:
            dims.append(DimensionScore(
                name=dim_name, score=score, weight=weight,
                weighted_score=score * weight,
            ))
    return ProductScore(
        product_name=name, vendor=vendor, url=url,
        dimensions=dims, confidence=confidence,
    )


SAMPLE_LABELS = {"price": "Price", "quality": "Quality / Reliability"}

SAMPLE_FLAGS_RESPONSE = json.dumps({
    "flags": [{
        "severity": "warning",
        "field": "price",
        "message": "Price score contradicts snippet text",
        "suggestion": "Verify pricing data",
    }]
})


def make_mock_client(response_text=SAMPLE_FLAGS_RESPONSE):
    mock = MagicMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=response_text))]
    )
    return mock


# ── _make_client ────────────────────────────────────────────────

class TestMakeClient:
    def test_returns_none_when_no_key(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "")
        assert _make_client() is None

    def test_returns_client_when_key_present(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key-123")
        client = _make_client()
        assert client is not None
        assert client.api_key == "test-key-123"
        assert judge_module._AI_BASE_URL in str(client.base_url)


# ── _parse_flags ────────────────────────────────────────────────

class TestParseFlags:
    def test_valid_json_with_flags(self):
        ps = make_ps()
        content = json.dumps({
            "flags": [{
                "severity": "warning", "field": "price",
                "message": "test msg", "suggestion": "fix it",
            }]
        })
        flags = _parse_flags(content, ps)
        assert len(flags) == 1
        assert flags[0].severity == "warning"
        assert flags[0].field == "price"
        assert flags[0].product_vendor == "Test Product (TestVendor)"
        assert flags[0].source == "ai"

    def test_valid_json_empty_flags(self):
        ps = make_ps()
        flags = _parse_flags('{"flags": []}', ps)
        assert flags == []

    def test_json_list_format(self):
        ps = make_ps()
        content = json.dumps([
            {"severity": "info", "field": "quality",
             "message": "check", "suggestion": ""}
        ])
        flags = _parse_flags(content, ps)
        assert len(flags) == 1
        assert flags[0].field == "quality"

    def test_json_with_extra_text_uses_regex_fallback(self):
        ps = make_ps()
        content = (
            "Here are my findings:\n"
            '{"flags": [{"severity": "info", "field": "general", '
            '"message": "note", "suggestion": ""}]}\n'
            "That's all."
        )
        flags = _parse_flags(content, ps)
        assert len(flags) == 1

    def test_completely_invalid_text_returns_empty(self):
        ps = make_ps()
        flags = _parse_flags("not json at all", ps)
        assert flags == []

    def test_missing_flags_key_within_json(self):
        ps = make_ps()
        flags = _parse_flags('{"other": "data"}', ps)
        assert flags == []

    def test_bad_item_in_list_skips_gracefully(self):
        ps = make_ps()
        content = json.dumps([
            {"severity": "info", "field": "price",
             "message": "valid", "suggestion": ""},
            "not a dict",
            None,
        ])
        flags = _parse_flags(content, ps)
        assert len(flags) == 1

    def test_non_list_items_field_returns_empty(self):
        ps = make_ps()
        flags = _parse_flags('{"flags": "not_a_list"}', ps)
        assert flags == []


# ── _build_product_prompt ───────────────────────────────────────

class TestBuildProductPrompt:
    def test_includes_all_scores(self):
        ps = make_ps(dimensions=[
            ("price", 60, 0.25),
            ("quality", 70, 0.20),
        ])
        raw = {"snippet": "Test snippet", "raw_price": 49.99, "avg_rating": 4.3}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "moderate")
        assert "60/100" in prompt and "70/100" in prompt
        assert "Test snippet" in prompt

    def test_includes_threshold_instruction_strict(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "ok"}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "strict")
        assert "do NOT flag" in prompt

    def test_includes_threshold_instruction_lenient(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "ok"}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "lenient")
        assert "potential inconsistency" in prompt.lower()

    def test_uses_correct_default_for_unknown_threshold(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "ok"}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "unknown_value")
        assert "likely inconsistencies" in prompt

    def test_extra_snippets_appended(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "main", "extra_snippets": ["extra1", "extra2"]}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "moderate")
        assert "extra1" in prompt and "extra2" in prompt

    def test_truncates_long_text(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        long_text = "x" * 2000
        raw = {"snippet": long_text, "extra_snippets": []}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "moderate")
        assert len(prompt) < 3000

    def test_handles_empty_snippet(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "", "raw_price": None, "avg_rating": None}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "moderate")
        assert prompt is not None

    def test_includes_output_format_instructions(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "test"}
        prompt = _build_product_prompt(ps, raw, SAMPLE_LABELS, "moderate")
        assert '"flags"' in prompt
        assert "Valid severity" in prompt


# ── _cache_key ──────────────────────────────────────────────────

class TestCacheKey:
    def test_deterministic(self):
        ps = make_ps(url="https://example.com/p")
        key1 = _cache_key(ps, "consumer", "moderate")
        key2 = _cache_key(ps, "consumer", "moderate")
        assert key1 == key2

    def test_different_thresholds_give_different_keys(self):
        ps = make_ps()
        assert _cache_key(ps, "c", "strict") != _cache_key(ps, "c", "moderate")

    def test_different_products_give_different_keys(self):
        ps1 = make_ps(name="A", url="https://a.com")
        ps2 = make_ps(name="B", url="https://b.com")
        assert _cache_key(ps1, "c", "m") != _cache_key(ps2, "c", "m")


# ── Cache I/O ───────────────────────────────────────────────────

class TestCacheIO:
    def test_load_no_file(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_no_such_cache.json"))
        assert _load_cache() == {}

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        cache_file = tmp_path / ".judge_cache.json"
        monkeypatch.setattr(judge_module, "_CACHE_PATH", cache_file)
        data = {"key1": {"flags": [], "cached_at": 12345}}
        _save_cache(data)
        assert cache_file.exists()
        loaded = _load_cache()
        assert loaded == data

    def test_load_corrupted_file(self, tmp_path, monkeypatch):
        cache_file = tmp_path / ".judge_cache.json"
        cache_file.write_text("not json at all")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", cache_file)
        assert _load_cache() == {}


# ── _judge_product ──────────────────────────────────────────────

class TestJudgeProduct:
    def test_happy_path_returns_flags(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "test", "raw_price": 49.99, "avg_rating": 4.0}
        cache = {}
        client = make_mock_client()
        flags = _judge_product(client, ps, raw, SAMPLE_LABELS, "agnes-2.0-flash", "moderate", cache)
        assert len(flags) == 1
        assert flags[0].source == "ai"
        assert len(cache) == 1

    def test_cache_hit_returns_cached(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "test", "raw_price": 49.99, "avg_rating": 4.0}
        ckey = _cache_key(ps, list(SAMPLE_LABELS.values())[0], "moderate")
        cache = {
            ckey: {
                "flags": [{
                    "severity": "info", "field": "quality",
                    "message": "cached flag", "suggestion": "",
                }],
                "cached_at": time.time(),
            }
        }
        client = make_mock_client()
        flags = _judge_product(client, ps, raw, SAMPLE_LABELS, "agnes-2.0-flash", "moderate", cache)
        assert len(flags) == 1
        assert flags[0].message == "cached flag"

    def test_cache_expired_revalidates(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "test", "raw_price": 49.99, "avg_rating": 4.0}
        ckey = _cache_key(ps, list(SAMPLE_LABELS.values())[0], "moderate")
        cache = {
            ckey: {
                "flags": [{
                    "severity": "info", "field": "quality",
                    "message": "stale flag", "suggestion": "",
                }],
                "cached_at": time.time() - _CACHE_TTL - 3600,
            }
        }
        client = make_mock_client()
        flags = _judge_product(client, ps, raw, SAMPLE_LABELS, "agnes-2.0-flash", "moderate", cache)
        assert len(flags) == 1
        assert flags[0].message != "stale flag"

    def test_llm_error_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {"snippet": "test"}
        cache = {}
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API failure")
        flags = _judge_product(client, ps, raw, SAMPLE_LABELS, "agnes-2.0-flash", "moderate", cache)
        assert flags == []

    def test_empty_raw_input(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = {}
        cache = {}
        client = make_mock_client()
        flags = _judge_product(client, ps, raw, SAMPLE_LABELS, "agnes-2.0-flash", "moderate", cache)
        assert isinstance(flags, list)


# ── judge_batch ─────────────────────────────────────────────────

class TestJudgeBatch:
    def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        result = judge_batch([ps], [{"url": "https://example.com/product"}])
        assert result == {}

    def test_empty_products_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        with patch("judge._make_client", return_value=make_mock_client()):
            result = judge_batch([], [])
        assert result == {}

    def test_all_products_no_flags_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = [{"url": ps.url, "snippet": "Fine product"}]
        with patch("judge._make_client", return_value=make_mock_client('{"flags": []}')):
            result = judge_batch([ps], raw)
        assert result == {}

    def test_product_with_flags_in_result(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(name="Toner", vendor="HP", dimensions=[("price", 70, 0.25)])
        raw = [{"url": ps.url, "snippet": "Overpriced item", "raw_price": 200.0, "avg_rating": 3.0}]
        with patch("judge._make_client", return_value=make_mock_client()):
            result = judge_batch([ps], raw)
        key = "Toner::HP"
        assert key in result
        assert len(result[key].flags) == 1
        assert result[key].adjusted_confidence < 1.0

    def test_preset_labels_used(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[
            ("unit_price", 50, 0.25),
            ("supplier_trust", 50, 0.15),
        ])
        raw = [{"url": ps.url, "snippet": "Business product"}]
        with patch("judge._make_client", return_value=make_mock_client()):
            result = judge_batch([ps], raw, preset="business")
        # Should not crash — business labels differ from consumer
        assert isinstance(result, dict)

    def test_confidence_floor(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_AI_API_KEY", "test-key")
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        many_flags = {"flags": [{"severity": "error", "field": "price", "message": "x", "suggestion": "y"}] * 10}
        ps = make_ps(name="Toner", vendor="HP", dimensions=[("price", 50, 0.25)], confidence=0.3)
        raw = [{"url": ps.url, "snippet": "test"}]
        with patch("judge._make_client", return_value=make_mock_client(json.dumps(many_flags))):
            result = judge_batch([ps], raw)
        key = "Toner::HP"
        if key in result:
            assert result[key].adjusted_confidence >= 0.25


# ── Cross-Product ────────────────────────────────────────────────

SAMPLE_CROSS_FLAGS = json.dumps({
    "flags": [
        {"product_index": 1, "severity": "warning", "field": "price",
         "message": "Same price as #2 but price score 20pts higher",
         "suggestion": "Check pricing data"},
    ]
})

CONSUMER_LABELS = {
    "price": "Price", "quality": "Quality", "shipping_speed": "Shipping",
    "vendor_reputation": "Vendor Rep", "warranty_service": "Warranty",
    "sustainability": "Sustainability", "secondhand_condition": "Secondhand",
    "preference_alignment": "Preference",
}


class TestBuildCrossPrompt:
    def test_includes_all_products(self):
        ps1 = make_ps(name="Toner A", vendor="HP", dimensions=[("price", 80, 0.25)])
        ps2 = make_ps(name="Toner B", vendor="Dell", dimensions=[("price", 60, 0.25)])
        raw = [{"url": ps1.url, "raw_price": 50.0, "avg_rating": 4.0},
               {"url": ps2.url, "raw_price": 55.0, "avg_rating": 3.5}]
        prompt = _build_cross_prompt([ps1, ps2], raw, CONSUMER_LABELS, "moderate")
        assert "Toner A" in prompt and "Toner B" in prompt
        assert "HP Inc." in prompt and "Dell Technologies" in prompt

    def test_includes_numeric_heuristics(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "moderate")
        assert ">15 points" in prompt
        assert "0.3 stars" in prompt
        assert ">25 points" in prompt

    def test_includes_threshold_strict(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "strict")
        assert "do NOT flag" in prompt

    def test_includes_threshold_lenient(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "lenient")
        assert "potential inconsistency" in prompt

    def test_includes_section_headings(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "moderate")
        assert "Price vs Price-Score" in prompt
        assert "Rating vs Quality-Score" in prompt
        assert "Vendor Reputation Consistency" in prompt
        assert "Score Range Anomalies" in prompt
        assert "Data Quality Clues" in prompt

    def test_includes_score_values(self):
        ps = make_ps(dimensions=[("price", 72, 0.25), ("quality", 85, 0.20)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "moderate")
        assert "Price=72" in prompt
        assert "Quality=85" in prompt

    def test_output_format_instructions(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        prompt = _build_cross_prompt([ps], [{"url": ps.url}], CONSUMER_LABELS, "moderate")
        assert "product_index" in prompt
        assert '"flags"' in prompt

    def test_raw_price_and_rating_included(self):
        ps = make_ps(dimensions=[("price", 70, 0.25)])
        raw = [{"url": ps.url, "raw_price": 89.99, "avg_rating": 4.5}]
        prompt = _build_cross_prompt([ps], raw, CONSUMER_LABELS, "moderate")
        assert "89.99" in prompt
        assert "4.5" in prompt

    def test_empty_snippets_ok(self):
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        raw = [{"url": ps.url}]
        prompt = _build_cross_prompt([ps], raw, CONSUMER_LABELS, "moderate")
        assert prompt is not None


class TestParseCrossFlags:
    def test_valid_json_returns_flags(self):
        scored = [make_ps(name="Toner", vendor="HP")]
        content = SAMPLE_CROSS_FLAGS
        result = _parse_cross_flags(content, scored)
        key = "Toner::HP"
        assert key in result
        assert len(result[key]) == 1
        assert result[key][0].severity == "warning"
        assert result[key][0].source == "ai"

    def test_empty_flags_returns_empty_dict(self):
        ps = make_ps()
        result = _parse_cross_flags('{"flags": []}', [ps])
        assert result == {}

    def test_skip_invalid_product_index(self):
        ps = make_ps(name="Toner", vendor="HP")
        content = json.dumps({
            "flags": [{"product_index": 99, "severity": "warning",
                       "field": "price", "message": "bad idx", "suggestion": ""}]
        })
        result = _parse_cross_flags(content, [ps])
        assert result == {}

    def test_skip_zero_product_index(self):
        ps = make_ps(name="Toner", vendor="HP")
        content = json.dumps({
            "flags": [{"product_index": 0, "severity": "info",
                       "field": "general", "message": "ok", "suggestion": ""}]
        })
        result = _parse_cross_flags(content, [ps])
        assert result == {}

    def test_skip_non_dict_items(self):
        ps = make_ps(name="Toner", vendor="HP")
        content = json.dumps({"flags": ["not a dict", None, 123]})
        result = _parse_cross_flags(content, [ps])
        assert result == {}

    def test_malformed_json_uses_regex_fallback(self):
        ps = make_ps(name="Toner", vendor="HP")
        content = (
            "Here are my findings:\n"
            '{"flags": [{"product_index": 1, "severity": "warning", '
            '"field": "price", "message": "inconsistent", "suggestion": "verify"}]}\n'
            "That's all."
        )
        result = _parse_cross_flags(content, [ps])
        key = "Toner::HP"
        assert key in result
        assert len(result[key]) == 1

    def test_completely_invalid_text_returns_empty(self):
        ps = make_ps()
        result = _parse_cross_flags("not json at all", [ps])
        assert result == {}

    def test_multiple_products_multiple_flags(self):
        ps1 = make_ps(name="A", vendor="HP")
        ps2 = make_ps(name="B", vendor="Dell")
        content = json.dumps({
            "flags": [
                {"product_index": 1, "severity": "warning", "field": "price",
                 "message": "m1", "suggestion": "s1"},
                {"product_index": 2, "severity": "info", "field": "quality",
                 "message": "m2", "suggestion": "s2"},
                {"product_index": 1, "severity": "error", "field": "general",
                 "message": "m3", "suggestion": "s3"},
            ]
        })
        result = _parse_cross_flags(content, [ps1, ps2])
        assert len(result["A::HP"]) == 2
        assert len(result["B::Dell"]) == 1


class TestJudgeCrossProducts:
    def test_happy_path_returns_flags(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps1 = make_ps(name="A", vendor="HP", dimensions=[("price", 80, 0.25)])
        ps2 = make_ps(name="B", vendor="Dell", dimensions=[("price", 50, 0.25)])
        raw = [{"url": ps1.url, "raw_price": 50.0, "avg_rating": 4.0},
               {"url": ps2.url, "raw_price": 55.0, "avg_rating": 3.5}]
        client = make_mock_client(SAMPLE_CROSS_FLAGS)
        result = _judge_cross_products(client, [ps1, ps2], raw, CONSUMER_LABELS, "agnes-2.0-flash", "moderate")
        key = "A::HP"
        assert key in result
        assert len(result[key]) == 1
        assert result[key][0].field == "price"

    def test_llm_error_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API failure")
        result = _judge_cross_products(client, [ps], [{"url": ps.url}], CONSUMER_LABELS, "agnes-2.0-flash", "moderate")
        assert result == {}

    def test_no_flags_returns_empty(self, monkeypatch):
        monkeypatch.setattr(judge_module, "_CACHE_PATH", Path("/tmp/_test_cache.json"))
        ps = make_ps(dimensions=[("price", 50, 0.25)])
        client = make_mock_client('{"flags": []}')
        result = _judge_cross_products(client, [ps], [{"url": ps.url}], CONSUMER_LABELS, "agnes-2.0-flash", "moderate")
        assert result == {}


# ── Threshold constants ─────────────────────────────────────────

class TestThresholdConfig:
    def test_strict_temp_is_zero(self):
        assert _THRESHOLD_TEMPS["strict"] == 0.0

    def test_moderate_temp(self):
        assert _THRESHOLD_TEMPS["moderate"] == 0.1

    def test_lenient_temp(self):
        assert _THRESHOLD_TEMPS["lenient"] == 0.3

    def test_all_thresholds_have_values(self):
        for t in ("strict", "moderate", "lenient"):
            assert t in _THRESHOLD_PROMPTS
            assert t in _THRESHOLD_TEMPS

    def test_prompts_are_distinct(self):
        assert _THRESHOLD_PROMPTS["strict"] != _THRESHOLD_PROMPTS["lenient"]
