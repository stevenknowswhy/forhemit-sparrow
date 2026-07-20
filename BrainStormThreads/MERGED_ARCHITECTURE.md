# Sparrow — Merged Architecture Specification

**Version:** 1.0  
**Date:** July 20, 2026  
**Status:** Approved by stakeholder

---

## 1. Architectural Foundation

### Primary Reference: Kimi (Complete Engine) + Gemini (Multi-Agent System)

We merge **Kimi's** production-ready technical depth with **Gemini's** elegant multi-agent orchestration.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPARROW CORE (Rust/Tauri)                    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ENCRYPTED    │  │ PII SCRUBBER │  │ PREFERENCE LEARNER   │  │
│  │ SQLITE DB    │  │ (Context-    │  │ (On-device vector    │  │
│  │ (OPFS/Local) │  │  Aware, not  │  │  embeddings)         │  │
│  │              │  │  Paranoid)   │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MULTI-AGENT ORCHESTRATOR                    │   │
│  │  (Gemini's 3-agent pattern, orchestrated by Kimi's       │   │
│  │   sandbox infrastructure)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ SCHEDULER    │  │ MONETIZATION │  │ UI/FRONTEND          │  │
│  │ (Adaptive    │  │ ENGINE       │  │ (Tauri + HTML/CSS)   │  │
│  │  Frequency)  │  │ (Hybrid)     │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Three-Agent System (Gemini's Pattern)

Each agent runs inside Kimi's sandbox infrastructure:

| Agent | Role | Orchestrates |
|-------|------|-------------|
| **Scout Agent** | Discovers alternatives across 3 tiers of sources | Builds anonymized search queries, dispatches parallel research |
| **Evaluator Agent** | Applies 8-dimension rubric, filters by quality thresholds | Scores, ranks, applies secondhand/auction adjustments |
| **Analyst Agent** | Calculates delta, generates report, runs sensitivity analysis | Formats executive summary, Monte Carlo scenarios, TCO projections |

### Sandbox Architecture (Kimi's Infrastructure)

```
┌─────────────────────────────────────────────────────────────┐
│  LOCAL MACHINE                                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SPARROW CORE (Rust)                                │   │
│  │  • Encrypted SQLite database                        │   │
│  │  • PII scrubber (context-aware)                     │   │
│  │  • Preference learner (sqlite-vss embeddings)       │   │
│  │  • Adaptive scheduler                               │   │
│  └────────────────────────┬────────────────────────────┘   │
│                           │                                 │
│              ┌────────────▼────────────┐                   │
│              │  RESEARCH SANDBOX       │  ← Spins up per  │
│              │  (Per-job isolation)    │    comparison job│
│              ├─────────────────────────┤                   │
│              │ • Headless browser      │                   │
│              │ • Proxy rotation        │                   │
│              │ • Rate limiter          │                   │
│              │ • Cookie jar (empty)    │                   │
│              │ • Fingerprint masked    │                   │
│              │ • Firecracker/WASM      │                   │
│              └────────────┬────────────┘                   │
│                           │                                 │
│              ┌────────────▼────────────┐                   │
│              │  EXTERNAL WEB           │  ← Anonymized    │
│              │  (PII-stripped only)    │    queries only  │
│              └─────────────────────────┘                   │
│                                                             │
│  Sandbox destroyed after job completion. No persistent state │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Input: Excel / Google Sheets (MVP)

**Decision:** Skip bank/Plaid ingestion for MVP. Start with file-based input.

### Supported Input Methods
| Method | Format | Parsing Approach |
|--------|--------|-----------------|
| **CSV Export** | Bank/credit card CSV | Regex + merchant fingerprinting |
| **Excel (.xlsx)** | QBO export, spreadsheet | rust_xlsxwriter + structured parsing |
| **Google Sheets** | Via Google Sheets API | OAuth2 service account, read-only |
| **PDF Invoices** | Merchant statements | Multi-modal OCR (Tesseract + layout analysis) |

### Data Flow
```
User uploads Excel/CSV/PDF
        ↓
PII Scrubber (context-aware)
        ↓
Transaction Fingerprinting Engine
        ↓
Pattern Clustering (identify recurring items)
        ↓
Research Brief → Scout Agent → Evaluator Agent → Analyst Agent
        ↓
Comparison Report → User Review → Invoke/Reject
        ↓
Savings Ledger (encrypted local)
```

### Transaction Fingerprinting
```rust
// Pseudo-struct for parsed transaction
pub struct TransactionFingerprint {
    merchant_hash: String,      // anonymized, not raw name
    category: String,           // "office_supplies", "shipping", etc.
    product_type: String,       // "toner_cartridge", "corrugated_box"
    unit_price: f64,
    quantity: u32,
    frequency: PurchaseCadence, // daily, weekly, monthly, quarterly, yearly
    last_purchase: NaiveDate,
    total_spend_ytd: f64,
    confidence: f64,            // 0.0-1.0 how sure we are about the product
}
```

---

## 3. Monetization Model (DeepSeek's Hybrid)

### Fee Structure

| Component | Detail | Rationale |
|-----------|--------|-----------|
| **Free Discovery** | Always free — any user can see savings opportunities | Zero friction onboarding |
| **Verification Fee** | $5 for deep-dive comparison report (waived for Premium) | Covers API/scrape costs for detailed analysis |
| **Success Fee (Individual)** | 0.5% of measured savings over stated measurement period | Aligned incentives |
| **Success Fee (Business)** | 1.5% of measured savings over stated measurement period | B2B requires more complex workflows |
| **Minimum Fee (Floor)** | $2.00 per verified savings event | Protects unit economics on small wins |
| **Cap (Ceiling)** | $2,500 per single vendor optimization | Prevents bill shock on enterprise deals |
| **Premium Tier** | $99/month — includes free verification, auto-execution enabled | Recurring revenue, power users |

### Fee Calculation Precision
> **Wording:** "0.5% (or 1.5% for business) of the **measured savings** over the **stated measurement period**"
>
> NOT 0.5% of the purchase amount. NOT 0.5 percentage points.

### Every Recommendation Must Show:
1. Baseline spend (what you pay now)
2. Measurement period (annualized or contract term)
3. Projected savings
4. Fee (with min/cap applied)
5. Verification method (how savings are confirmed)
6. Net benefit to user

### Premium Tier Features
| Feature | Free | Business | Premium |
|---------|------|----------|---------|
| Discovery | ✓ | ✓ | ✓ |
| Verification | $5/report | $25/report | Waived |
| Manual Execution Fee | 0.5% (min $2 / cap $500) | 1.5% (min $10 / cap $2,500) | Waived |
| Auto-Execution Fee | Disabled | Disabled | 1.0% success fee |
| Advanced Analytics | Basic | Full | Full + TCO projections |
| API Access | — | — | Webhook exports |

---

## 4. Comparison Rubric (Kimi's 8 Dimensions)

### Default Weights (User-Adjustable)

| # | Dimension | Default Weight | What It Measures | Data Sources |
|---|-----------|---------------|------------------|-------------|
| 1 | **Unit Price** | 25% | Base cost per unit, bulk discounts, tier pricing | Scraped pricing pages, APIs |
| 2 | **Shipping & Freight** | 15% | Cost to deliver, speed options, free thresholds | Real-time shipping calculators |
| 3 | **Quality Score** | 20% | Review sentiment, return rate, defect history, warranty | Review aggregation, BBB, Trustpilot |
| 4 | **Speed & Reliability** | 10% | Lead time, stock availability, backorder risk | Inventory APIs, delivery estimates |
| 5 | **Total Landed Cost** | 15% | Price + shipping + tax + duties + handling | Calculated composite |
| 6 | **Supplier Trust** | 8% | Years in business, rating volume, complaint resolution | Business registries, review platforms |
| 7 | **Compatibility Risk** | 5% | Spec match confidence, integration effort, return ease | Product specs, compatibility databases |
| 8 | **Sustainability** | 2% | Eco-certifications, carbon footprint, ethical sourcing | Certifications, supplier disclosures |

### Score Calculation
```
COMPARISON_SCORE = Σ (Dimension_Score_i × Weight_i)

Where each Dimension_Score is normalized 0-100:
  100 = Best in class / exceeds current vendor
  50  = Comparable to current vendor
  0   = Unacceptable / fails minimum threshold

MINIMUM VIABLE SCORE: 65
(Anything below 65 is suppressed from user view)
```

### Category-Specific Weight Adjustments
Different categories naturally weight dimensions differently. The agent suggests defaults:

| Category | Heavier Weight On | Lighter Weight On |
|----------|-------------------|-------------------|
| Office Supplies | Unit Price (30%), Speed (15%) | Sustainability (1%) |
| IT Hardware | Quality (25%), Trust (12%) | Sustainability (1%) |
| Furniture | Quality (22%), Compatibility (8%) | Sustainability (4%) |
| SaaS / Digital | Compatibility (10%), Quality (22%) | Shipping (0%), Freight (0%) |
| Consumables | Unit Price (30%), TCO (20%) | Sustainability (3%) |

---

## 5. Secondhand / Refurbished / Auction Logic (DeepSeek + Kimi Merge)

### Toggle System (Kimi's UX)

```
┌─────────────────────────────────────────────────────┐
│  🔍 DEAL HUNTING PREFERENCES                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [✓] New items only                                 │
│  [ ] Include certified refurbished                  │
│  [ ] Include open-box / like-new                    │
│  [ ] Include auction sites (eBay, GovDeals, etc.)   │
│                                                     │
│  Minimum seller rating: [4.5 stars ▼]               │
│  Maximum acceptable defect rate: [3% ▼]              │
│  Warranty required: [✓] Yes  [ ] No                 │
│                                                     │
│  [Save Preferences]                                 │
└─────────────────────────────────────────────────────┘
```

### Progressive Quality Penalties (Kimi)

| Toggle State | Quality Adjustment | Badge | Risk Flag |
|-------------|-------------------|-------|-----------|
| New only | Baseline (0%) | — | None |
| + Refurbished | -10% | "Refurbished" | Moderate |
| + Open-Box | -5% | "Open-Box" | Low |
| + Auction | -15% | "Auction" | High |

### Condition Grading Scale (DeepSeek)

| Grade | Description | Quality Multiplier | Warranty Expectation |
|-------|-------------|-------------------|---------------------|
| New | Factory sealed | 1.0 | Full OEM |
| Open Box | Returned, unopened | 0.95 | Full OEM or 90-day |
| Refurbished-Certified | Manufacturer certified | 0.9 | 12-month OEM-equivalent |
| Refurbished-Seller | Seller-refurbished | 0.75 | 30-90 day seller warranty |
| Used-Like New | Minimal signs of use | 0.85 | 30-day return only |
| Used-Good | Moderate wear | 0.7 | No warranty |
| Acceptable | Visible damage, functional | 0.5 | No warranty |

### Auction Price Prediction (DeepSeek)

The agent does NOT use the current bid as the price. Instead:

```
PROJECTED_FINAL_PRICE = f(
  historical_final_bids_similar_items,
  time_remaining_acceleration_curve,
  bid_count_velocity,
  seller_reputation_weight,
  reserve_price_met
)

Output: "90th-percentile likely win estimate: $38.00"
Flag: "Auction — price not guaranteed"
```

### Risk Warnings (Kimi's UX)

```
⚠️ SPARROW WARNING:
You've returned 2 refurbished items in the past 12 months.
Your quality threshold is set to 70. This item scores 62.
[Show Anyway]  [Hide Low-Quality Items]
```

---

## 6. Competitive Positioning

### Market Wedge: SMB Operating Supplies

Starting categories (ordered by ease of implementation):
1. Shipping & packaging supplies
2. Office consumables (paper, toner, pens)
3. Printer supplies
4. Janitorial products
5. Facility maintenance (filters, bulbs, batteries)
6. Restaurant disposables

### Positioning Statement

> **"Rocket Money finds your subscriptions. Honey finds coupons. Ramp controls your spend. Expense consultants charge 30% to negotiate your bills. Sparrow is the first private, local buying agent that continuously hunts for better deals across everything you buy — and only charges 0.5% when you actually save."**

### Defensive Moats

| Moat | Action |
|------|--------|
| **Local-first trust** | Open-source the PII scrubber for audit |
| **Speed** | Rust performance — sub-second analysis |
| **Self-improving network** | Anonymized preference learning improves agent globally |
| **Category depth** | Build the best shipping-supplies comparison engine on Earth |
| **Switching cost** | Once Sparrow learns your preferences, retraining a competitor is painful |

---

## 7. MVP Priority Roadmap

### Phase 1: Core Foundation
- [ ] Rust/Tauri project scaffold
- [ ] Encrypted SQLite database (local file)
- [ ] PII scrubber (context-aware, not paranoid)
- [ ] Excel/CSV file upload parser
- [ ] Transaction fingerprinting engine
- [ ] Basic category detection (rule-based)

### Phase 2: Research Engine
- [ ] Research sandbox (containerized per-job isolation)
- [ ] Scout Agent — multi-source parallel search
- [ ] Data source integration: Amazon PAA, Google Shopping, eBay
- [ ] Evaluator Agent — 8-dimension rubric scoring
- [ ] Basic comparison report generation

### Phase 3: User Experience
- [ ] Tauri frontend — dashboard with expense matrix
- [ ] Side-by-side comparison UI
- [ ] Invoke/Reject decision flow
- [ ] Savings ledger (projected vs. realized)
- [ ] Fee calculation display (baseline → savings → fee → net)

### Phase 4: Intelligence
- [ ] Preference learner (on-device vector embeddings)
- [ ] Adaptive scheduler (frequency by purchase cadence)
- [ ] Secondhand/auction toggle with condition grading
- [ ] Auction price prediction model
- [ ] Risk warnings (cross-reference with user history)

### Phase 5: Advanced Features
- [ ] Analyst Agent — Monte Carlo sensitivity analysis
- [ ] What-If scenario builder
- [ ] Carrying cost of capital overlay
- [ ] Friction/risk degradation index (green/yellow/red)
- [ ] TCO calculator (1yr / 3yr / 5yr horizons)
- [ ] "Negotiate Instead" mode (draft email to current vendor)
- [ ] Premium tier implementation ($99/mo, auto-execution)

---

## 8. Data Source Tiers (Kimi)

### Tier 1: Structured APIs (Most Reliable)

| Source | API | Cost | Data |
|--------|-----|------|------|
| Amazon | Product Advertising API | Free (affiliate) | Price, ratings, Prime, stock |
| Google Shopping | Shopping API | $0.005/query | Prices across retailers |
| eBay | Selling API | Free (5K calls/day) | Price, condition, seller rating |
| Walmart | API | Free | Price, stock, shipping |
| Best Buy | API | Free | Price, open-box, store pickup |

### Tier 2: Scraping Targets (Sandbox Required)

| Source | Method | Data |
|--------|--------|------|
| B&H Photo | ScrapingBee/Zyte | Price, stock, business pricing |
| Newegg | ScrapingBee/Zyte | Price, stock, seller ratings |
| CDW | Bright Data | Enterprise pricing, bulk discounts |
| Office Depot | ScrapingBee | Price, stock, delivery |
| Manufacturer sites | Firecrawl Agent | MSRP, warranty, specs |

### Tier 3: Quality & Trust Data

| Source | Method | Data |
|--------|--------|------|
| ReviewMeta / Fakespot | API | Review authenticity score |
| BBB.org | Scraping | Business rating, complaints |
| Trustpilot | API | Seller rating, review volume |
| Reddit forums | Scraping | Real user experiences, defects |

---

## 9. Cost Estimates Per Comparison

| Component | Cost | Time |
|-----------|------|------|
| Tier 1 API calls (3 sources) | ~$0.015 | ~200ms |
| Tier 2 scraping (2 sources) | ~$0.040 | ~2-5 seconds |
| LLM evaluation (Evaluator Agent) | ~$0.010 | ~1-2 seconds |
| LLM report generation (Analyst Agent) | ~$0.005 | ~1 second |
| **Total per comparison** | **~$0.07** | **~5-10 seconds** |

**Break-even:** At $0.07 per comparison and 0.5% success fee, the minimum savings event must generate ≥$400 in annual savings to cover API cost. This validates the "Proof of Funds" gate — ignoring expenses below a threshold protects unit economics.

---

*This document merges the best elements from Kimi's complete engine, Gemini's multi-agent elegance, DeepSeek's hybrid monetization, and all models' competitive consensus. Ready for implementation planning.*
