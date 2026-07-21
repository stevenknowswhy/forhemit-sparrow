# Sparrow Rubric Documentation

## Overview

Sparrow evaluates every product using a standardized rubric across multiple dimensions. Each dimension is scored 0–100, weighted, and summed to produce a total weighted score. Two presets are available: **Consumer** (8 dimensions, for personal purchasing) and **Business / CFO** (7 dimensions, for procurement decisions).

An **uncertainty penalty** is applied when data is missing — the confidence score multiplies the total.

---

## Consumer Preset

8 dimensions weighted for personal buying decisions. Balances price and quality with moderate emphasis on shipping speed and vendor trust.

| # | Dimension | Weight |
|---|-----------|--------|
| 1 | **Price** | 25% |
| 2 | **Quality / Reliability** | 20% |
| 3 | **Shipping Speed** | 15% |
| 4 | **Vendor Reputation** | 15% |
| 5 | **Warranty / Service** | 10% |
| 6 | **Sustainability** | 5% |
| 7 | **Secondhand Condition** | 5% |
| 8 | **Preference Alignment** | 5% |

**Total: 100%**

### 1. Price (25%)

**Score = 100 × (1 − (vendor_price − min_price) / (max_price − min_price))**

- Lowest price in batch = 100
- Highest price in batch = 0
- Linear interpolation between min/max
- If all prices are identical → 100 for all
- Missing price → 50 (default)

### 2. Quality / Reliability (20%)

**Score = min(100, (avg_rating / 5.0 × 70) + min(30, 15 × log₁₀(review_count + 1)))**

- Average rating contributes up to 70 points (4:1 ratio)
- Review volume contributes up to 30 points on a log scale (diminishing returns: ~10 reviews → 15pts, 100 → 30pts)
- Missing rating → 50 (default)

### 3. Shipping Speed (15%)

**Score = clamp(100 − (days × 8) + (free_shipping ? 15 : 0), 0, 100)**

- Each day of delay costs 8 points
- Free shipping adds 15 bonus points
- Missing data → 50

### 4. Vendor Reputation (15%)

**Score = clamp(50 + trustpilot_score × 6 + bbb_bonus + (warranty ? 10 : 0) + (return_policy ? 10 : 0), 0, 100)**

- Starting baseline: 50
- Trustpilot rating (0–5): contributes up to 30 points
- BBB rating: A+ = +20, A = +15, A- = +10, B+ = +5, B = 0, C = −10, F = −20
- Warranty presence: +10
- Return policy: +10
- If vendor sentiment is extracted from text (positive/negative keyword analysis), the score blends: `score × 0.4 + sentiment × 0.6`
- Missing data → 50

### 5. Warranty / Service (10%)

**Score = 70 if warranty_found else 50**

- Boolean check: if any warranty/guarantee keyword found in text
- Missing data → 50 (default)

### 6. Sustainability (5%)

**Score = min(100, eco_keywords × 15)**

- Each matched keyword (eco-friendly, sustainable, energy star, recycled, carbon neutral, green, renewable) adds 15 points
- Default: 40 (moderate penalty for unknown)

### 7. Secondhand Condition (5%)

**Score = base_score × grade_multiplier**

- Base: 50 (always, no data source yet)
- Grade multipliers applied when `is_secondhand` is set:

| Grade | Multiplier |
|-------|-----------|
| Excellent | 0.9 |
| Good | 0.7 |
| Fair | 0.5 |
| Acceptable | 0.3 |

- Not yet populated from real data — always 50

### 8. Preference Alignment (5%)

**Score = 50 (always)**

- Not yet populated from real data.

---

## Business / CFO Preset

7 dimensions weighted for total cost of ownership in procurement. Merges shipping + freight into a single logistics dimension. Lower weight on sustainability.

| # | Dimension | Weight |
|---|-----------|--------|
| 1 | **Unit Price** | 25% |
| 2 | **Quality Score** | 20% |
| 3 | **Supplier Trust** | 15% |
| 4 | **Compatibility Risk** | 13% |
| 5 | **Logistics Score** | 15% |
| 6 | **Speed & Reliability** | 10% |
| 7 | **Sustainability** | 2% |

**Total: 100%**

### 1. Unit Price (25%)

Identical algorithm to Consumer Price dimension.

### 2. Quality Score (20%)

Identical algorithm to Consumer Quality dimension.

### 3. Supplier Trust (15%)

Identical algorithm to Consumer Vendor Reputation dimension.

### 4. Compatibility Risk (13%)

**Score = 75 (always)**

- Not yet populated from real data. Defaulting high since most search results are known-compatible.

### 5. Logistics Score (15%)

**Score =**
- 100 if free shipping detected
- `clamp(100 × (1 − cost / max(20, cost×2)), 0, 100)` if shipping cost data available
- Falls back to Speed & Reliability algorithm if only shipping days are known
- 50 if no data

### 6. Speed & Reliability (10%)

**Score = clamp(100 − (days × 8) + (free_shipping ? 15 : 0), 0, 100)**

Identical algorithm to Consumer Shipping Speed dimension.

### 7. Sustainability (2%)

Identical algorithm to Consumer Sustainability dimension.

---

## Uncertainty Penalty

When not all dimensions have real data, a confidence multiplier reduces the total score:

```
confidence = 0.5 + 0.5 × (dimensions_with_data / total_dimensions)
```

- All dimensions with data: confidence = 1.0 (no penalty)
- Half with data: confidence = 0.75
- None with data: confidence = 0.5

The confidence is applied multiplicatively to `total_weighted_score`.

---

## Reference Vendor Scoring

When `--reference-vendor` is specified, the reference vendor's dimension scores become the baseline (50). Other products are scored relative:

- If product score ≥ reference: `score = min(100, 50 + delta × 1.0)`
- If product score < reference: `score = max(0, 50 + delta × 1.0)` (delta is negative)

This creates a centered comparison where the current vendor is always at ~50 and alternatives are scored above/below.

---

## Data Quality Indicators

Each dimension tracks whether its score is **data-backed** (●) or **defaulted** (○):

| Indicator | Meaning |
|-----------|---------|
| ● | Score computed from real search/extraction data |
| ○ | Score defaulted to 50 (or preset default) due to missing data |

Reports display the ratio: "X/Y dimensions with data".

---

## Score Interpretation

| Range | Meaning |
|-------|---------|
| 85–100 | Excellent — verified across multiple dimensions |
| 70–84 | Good — minor data gaps or trade-offs |
| 50–69 | Adequate — significant defaults or mediocre scores |
| 0–49 | Poor — avoid unless price is critical |

---

## Preset Customization

Weights can be overridden per-run:

```bash
python run.py "HP 64A toner" --custom-weights '{"price": 0.35, "quality": 0.25}'
```

Custom weights replace the preset weights entirely (fractional, sum not enforced but recommended ≈ 1.0).
