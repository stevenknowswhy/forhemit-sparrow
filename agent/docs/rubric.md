# The 8-Dimension Rubric — Transparent Product Scoring

## Overview

Sparrow evaluates every product using a standardized, transparent rubric across 8 dimensions. Each dimension is scored 0–100 and weighted to produce a total weighted score. The rubric is designed to reflect **total cost of ownership**, not just sticker price.

## Dimension Weights

| # | Dimension | Weight | Why It Matters |
|---|-----------|--------|----------------|
| 1 | **Price** | 25% | The biggest factor in expense reduction |
| 2 | **Quality** | 20% | Cheap but broken saves nothing |
| 3 | **Shipping Speed** | 15% | Downtime costs money |
| 4 | **Trust** | 15% | Vendor reliability prevents costly mistakes |
| 5 | **Warranty** | 10% | Protection against defects |
| 6 | **Sustainability** | 5% | Long-term environmental impact |
| 7 | **Secondhand** | 5% | Refurbished/open-box value |
| 8 | **Preference** | 5% | Alignment with user priorities |

**Total: 100%**

---

## Detailed Scoring Algorithms

### 1. Price (25%)

**Score = 100 − ((vendor_price − min_price) / (max_price − min_price)) × 100**

- Lowest price = 100 (perfect)
- Highest price = 0 (worst)
- Linear interpolation between min/max found in results
- Free shipping adds +5 bonus points
- Bulk discounts are factored in when available

**Example:** If Amazon charges $49.99, CDW $89.99, Staples $64.99:
- Amazon: 100 (lowest → perfect)
- Staples: 100 − ((64.99−49.99)/(89.99−49.99)) × 100 = 100 − 37.5 = 62.5
- CDW: 0 (highest → worst)

### 2. Quality (20%)

**Score = (avg_rating / 5.0 × 60) + (min(review_count / 1000, 1) × 40)**

- Average rating contributes 60% of the score
- Review volume contributes 40% (capped at 1,000 reviews)
- Missing rating defaults to 50 (neutral)

**Example:** 4.3★ with 1,200 reviews:
- Rating: (4.3/5.0) × 60 = 51.6
- Volume: min(1200/1000, 1) × 40 = 40
- Total: 91.6

### 3. Shipping Speed (15%)

**Score = max(0, 100 − (shipping_days × 15)) + (free_shipping ? 10 : 0)**

- Each day of delay costs 15 points
- Free shipping adds 10 bonus points
- Same-day delivery = 100 + 10 = 110 (capped at 100)
- Missing data defaults to 50

**Example:** 2 days, free shipping:
- Base: max(0, 100 − 30) = 70
- Free: +10
- Total: 80

### 4. Trust (15%)

**Score = (trustpilot_score / 5.0 × 50) + (has_warranty ? 25 : 0) + (has_return_policy ? 25 : 0)**

- Trustpilot rating contributes 50%
- Warranty presence adds 25%
- Return policy adds 25%
- Missing data defaults to 50

### 5. Warranty (10%)

**Score = base_coverage_months × 2 + (easy_claim ? 10 : 0)**

- Each month of coverage = 2 points
- Easy online claim process = +10
- Extended warranty available = +10
- Maximum: 100 (36+ months + easy claim + extended)

### 6. Sustainability (5%)

**Score = eco_certifications × 15 + recycled_content × 10 + carbon_offset × 5**

- FSC/EPEAT/Energy Star certification = 15 each
- Recycled packaging/content = 10
- Carbon offset program = 5
- Default: 40 (unknown)

### 7. Secondhand Condition (5%)

**Condition Grades:**
- New/Open Box: 100
- Like New: 85
- Very Good: 70
- Good: 55
- Fair: 40
- Poor: 20

**Penalty Multiplier:** Refurbished items get a 0.9x multiplier on the price dimension (already factored into the overall score).

### 8. Preference Alignment (5%)

**User-configurable.** When a user specifies preferences (brand, color, feature), Sparrow scores how well each product matches:

- Exact match = 100
- Partial match = 50–80
- No match = 0–20
- Default: 75 (assumed reasonable fit)

---

## How to Interpret Scores

| Range | Grade | Meaning |
|-------|-------|---------|
| 90–100 | A+ | Excellent — strong across all dimensions |
| 75–89 | A | Very Good — minor trade-offs |
| 60–74 | B | Good — acceptable with caveats |
| 45–59 | C | Fair — significant gaps |
| 30–44 | D | Poor — avoid unless price is critical |
| 0–29 | F | Unacceptable — major risks |

---

## Customization

Weights can be adjusted per-job by editing `scorer.py`:

```python
custom_weights = {
    "price": 0.30,        # Prioritize cost
    "quality": 0.15,      # Less weight on quality
    "shipping_speed": 0.20,  # Fast delivery matters
    # ... etc
}
```

The total weight must sum to 1.0 (100%).

---

## Transparency Note

All scores are derived from publicly available data. No opaque ML model determines the final ranking — the rubric is pure, auditable math. You can verify every score by checking the source data.
