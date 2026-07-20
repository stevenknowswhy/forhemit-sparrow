# Sparrow AI Brainstorm Comparison Report

**Date:** July 20, 2026  
**Project:** Sparrow — Local-First AI Expense Reduction Agent  
**Models Evaluated:** DeepSeek (×2), Google Gemini (×2), Kimi, Arena (Claude Sonnet 4 + others)

---

## Executive Summary

Seven AI model sessions were conducted to brainstorm and architect the Sparrow application — a local-first, Rust-based desktop app that autonomously reduces expenses by acting as a professional buying agent. Each model received the same core prompts but produced distinctly different architectures, strengths, and strategic perspectives.

### Key Findings at a Glance

| Model | Depth | Technical Detail | Strategic Insight | Unique Strength |
|-------|-------|-----------------|-------------------|----------------|
| **DeepSeek (Session 1)** | ★★★★★ | ★★★★☆ | ★★★☆☆ | Detailed sandbox + rubric architecture with auction logic |
| **Gemini (Session 1)** | ★★★★☆ | ★★★★★ | ★★★★☆ | Multi-agent workflow, friction scoring, carrying cost overlay |
| **Kimi** | ★★★★★ | ★★★★★ | ★★★★★ | Complete Sparrow engine with code, scoring, APIs, and learning loop |
| **Gemini (Session 2)** | ★★★★☆ | ★★★★☆ | ★★★★★ | OPFS/local SQLite, performance fee escrow, competitive battlecard |
| **DeepSeek (Session 2)** | ★★★★☆ | ★★★★☆ | ★★★★☆ | Efficiency/quality optimization blueprint with Monte Carlo analysis |
| **Arena (Claude Sonnet)** | ★★★☆☆ | ★★★☆☆ | ★★★★★ | Competitive landscape, "blue ocean" positioning, moat strategy |
| **SparrowApp.md** | N/A | N/A | N/A | Design narrative, efficiency, data hygiene, feedback panel |

---

## 1. Architecture Approaches

### DeepSeek (Session 1) — "The Digital Procurement Officer"
- **Sandbox:** Firecracker microVM or WASM per session (<100ms startup)
- **Network:** Allow-listed outbound only, enforced at namespace level
- **Pipeline:** Transaction → PII Strip → Research Brief → Multi-Source Query → Normalize → Score → Report
- **Key Innovation:** Structured LLM calls returning JSON schemas for spec matching; cross-validation against OEM datasheets

### Gemini (Session 1) — "The Multi-Agent System"
- **Sandbox:** Headless Chromium via playwright-rust, zero-state execution
- **Three Agents:** Scout (search), Evaluator (filter against quality/shipping/MOQ), Analyst (calculate delta, format report)
- **Storage:** WebAssembly SQLite over OPFS (Origin Private File System)
- **Key Innovation:** "Dynamic Cart Verification" — mock checkout to detect hidden costs (fuel surcharges, handling fees)

### Kimi — "The Complete Sparrow Engine"
- **Sandbox:** Containerized research environment per job, destroyed after completion
- **Infrastructure:** Rust-based with proxy rotation, rate limiting, fingerprint randomization
- **Data Sources:** 3 tiers — Structured APIs (Amazon, Google Shopping, eBay), Scraping targets (B&H, CDW), Quality/trust data (ReviewMeta, BBB, Trustpilot)
- **Key Innovation:** Full 8-dimension rubric with spec matching engine, "should cost" analysis, and TCO calculator

### Gemini (Session 2) — "The Privacy-First Platform"
- **Architecture:** Local Rust/Tauri app with OPFS database
- **PII Layer:** In-memory scrubbing pipeline — strip identifiers, tokenize categories, anonymize locations
- **Scheduling:** 3-tier matrix (High Velocity daily, Cyclical weekly, Long Tail monthly)
- **Key Innovation:** "Buyer Memory Cache" using embedded vector store (Qdrant) for implicit preference learning

### DeepSeek (Session 2) — "The Optimization Blueprint"
- **Approach:** Progressive disclosure scraping funnel (Tier 1 API → Tier 2 JSON-LD → Tier 3 Full Browser)
- **Caching:** Semantic caching with LanceDB in Rust
- **Parallelism:** Tokio async threads with "First-Win" cancellation pattern
- **Key Innovation:** Monte Carlo sensitivity analysis ("If you prioritize Price: Vendor C wins. If Speed: Vendor A wins.")

### Arena (Claude Sonnet) — "The Competitive Strategist"
- **Positioning:** Blue ocean — no direct competitor combines all capabilities
- **Moat Strategy:** Open-source PII scrubber, local-first trust, self-improving network effects
- **Key Innovation:** Competitive battlecard framework with threat matrix and defensive moats

---

## 2. Comparison Rubric Dimensions

All models converged on similar core dimensions, but with varying depth:

| Dimension | DeepSeek | Gemini | Kimi | Notes |
|-----------|----------|--------|------|-------|
| **Unit Price** | ✓ (20%) | ✓ | ✓ (25%) | Universal agreement |
| **Shipping & Freight** | ✓ (15%) | ✓ | ✓ (15%) | Kimi adds carrier API integration |
| **Quality Score** | ✓ (20%) | ✓ | ✓ (20%) | Kimi adds NLP review sentiment |
| **Speed/Lead Time** | ✓ | ✓ | ✓ (10%) | All model user-adjustable weights |
| **Total Landed Cost** | ✓ | ✓ | ✓ (15%) | Kimi includes duties/handling |
| **Supplier Trust** | ✗ | ✗ | ✓ (8%) | Kimi adds BBB, complaint resolution |
| **Compatibility Risk** | ✗ | ✗ | ✓ (5%) | Kimi adds spec matching confidence |
| **Sustainability** | ✗ | ✗ | ✓ (2%) | Kimi adds eco-certifications |
| **TCO (multi-year)** | ✓ | ✓ | ✓ | All models include |
| **Source Authority Weighting** | ✗ | ✓ | ✗ | Gemini adds verified purchaser boost |
| **Risk/Friction Index** | ✗ | ✓ | ✗ | Gemini adds green/yellow/red grading |
| **Carrying Cost of Capital** | ✗ | ✓ | ✗ | Gemini adds inventory holding friction |

---

## 3. Secondhand/Refurbished/Auction Logic

### DeepSeek — Most Detailed
- **Condition Grading Scale:** New → Open Box → Refurbished-Certified → Refurbished-Seller → Used-Like New → Used-Good → Acceptable
- **Auction Price Prediction:** Uses historical final bid data, time-adjusted bid acceleration curve, 90th-percentile "likely win" estimate
- **Risk Penalty:** Secondhand items get a condition score multiplier (Excellent 0.9, Good 0.7, Acceptable 0.5) on quality score
- **Sources:** eBay, B-Stock, Liquidation.com, GovDeals, Back Market, manufacturer refurbished stores

### Gemini — Most Practical
- **Rubric Adjustment:** Introduces "Risk Discount Factor" when toggle is ON
- **Quality Scan:** Actively checks return policies, warranty transferability, seller ratings
- **Output:** Includes "Secondary Market" badge on comparison cards

### Kimi — Most Comprehensive
- **Toggle States:** New only / +Refurbished / +Open-Box / +Auction (progressive inclusion)
- **Quality Penalties:** Refurbished -10%, Open-Box -5%, Auction -15%
- **User Warnings:** "You've returned 2 refurbished items in the past 12 months. Your quality threshold is 70. This item scores 62."
- **Sources:** eBay, Amazon Renewed, Back Market, GovDeals, Liquidation.com, Best Buy open-box

---

## 4. Monetization Models

### DeepSeek
- **Hybrid Model:** Free discovery → $5 paid verification → 0.5% success fee on execution
- **Minimum Fee:** $2.00 per verified savings event
- **Cap:** $2,500 lifetime per single vendor optimization
- **Business Rate:** 1.5% vs. 0.5% for individuals
- **Premium Tier:** Subscription for auto-execution (0% discovery fee, 1.0% auto-execution fee)

### Gemini (Session 1)
- **Pure Performance Fee:** 0.5% on invoked savings
- **Guardrails:** "Proof of Funds" gate — ignores expenses below threshold to protect API budget
- **Deprioritization:** Users who review but never invoke get downgraded in scheduler priority
- **Target:** B2B focus (higher absolute savings justify the fee)

### Gemini (Session 2)
- **Floor/Ceiling:** $5 minimum, $2,500 maximum per execution
- **Visual Loop:** Dashboard shows savings alongside micro-fee to emphasize value ratio
- **Escrow Architecture:** Tracks proposal → invocation → realized savings

### Kimi
- **Success Fee:** 0.5% of measured savings over stated measurement period
- **Precision Wording:** "0.5% of the measured savings" — not 0.5% of purchase amount
- **Transparency:** Every recommendation shows baseline, measurement period, fee, verification method, net benefit

### Arena (Claude Sonnet)
- **Positioning:** "ExpenseIQ" branding with $99/mo Pro tier
- **Fee:** 0.75% on auto-executed savings
- **Moat Strategy:** Open-source PII scrubber, community-built category depth

---

## 5. Efficiency & Quality Optimizations

### DeepSeek — "The Continuous Improvement Blueprint"
| Category | Optimization | Impact |
|----------|-------------|--------|
| **Caching** | Smart TTL based on price volatility | Faster, cheaper agent runs |
| **Pre-fetching** | Predictive scheduling 3-5 days before predicted reorder | Zero wait time |
| **Source Prioritization** | Tiered by category reliability score | 80% value from 20% API calls |
| **Cross-Item** | Basket analysis for free shipping thresholds | Additional consolidated savings |
| **Review Synthesis** | Local LLM generates pros/cons from reviews | Qualitative risk insight |
| **Price History** | Keepa/CamelCamelCamel sparklines + timing alerts | Avoid buying at peaks |
| **Negotiate Instead** | Draft email to current vendor with competitor leverage | Savings even without switching |
| **What-If Builder** | Manual variable adjustment with real-time score recalculation | Understand trade-offs |
| **Test Order** | Suggest small test order before full commitment | De-risk new suppliers |

### Gemini — "The Precision Architecture"
| Category | Optimization | Impact |
|----------|-------------|--------|
| **Progressive Scraping** | 3-tier funnel (API → JSON-LD → Full Browser) | 85-90% reduction in headless browser usage |
| **Mock Checkout** | Force real tax/shipping via simulated cart | Eliminates false-positive savings |
| **Spec Anchoring** | Industrial standard cross-referencing (GSM, steel gauge) | Prevents quality downgrades |
| **Carrying Cost** | Inventory holding friction calculation | Real net-adjusted savings |
| **Friction Index** | Green/Yellow/Red execution complexity grading | Manages user expectations |
| **Monte Carlo** | Sensitivity analysis on weight shifts | Shows "If Price vs. Speed" scenarios |
| **Confidence Filter** | Statistical confidence intervals on scores | Labels low-confidence as "Exploratory" |
| **Source Authority** | Weighted review scoring (.edu 1.5x, verified 1.2x, blog 0.5x) | Higher quality scores |

### Kimi — "The Full Stack Optimization"
| Category | Optimization | Impact |
|----------|-------------|--------|
| **Multi-Modal OCR** | Layout-aware PDF/table parsing | Fewer misclassified transactions |
| **Context-Aware Scrubbing** | Precision over paranoia in PII stripping | Better search results + trust |
| **Tiered Search** | Fast cheap sources first, expensive last | Faster, cheaper comparisons |
| **Dynamic Weight Learning** | Rubric adapts per category from user feedback | Personalized, relevant scores |
| **Show Your Work** | "Why not" explanations + human override | Trust + control |
| **Multi-Method Verification** | Audit trail for proven savings | Verified, not guessed |
| **Error Classification** | Cross-user anonymized learning | Gets smarter over time |
| **Progressive Disclosure** | Confidence meter + expert mode toggle | Power without overwhelm |

---

## 6. Competitive Landscape Consensus

All models agreed on the same competitive categories and white space:

### Consensus: No Direct Competitor Exists
Every model identified that no single product combines:
1. Bank/card/QuickBooks ingestion
2. Local encrypted storage
3. PII-isolated external research
4. Cross-category expense detection
5. Product/vendor comparison with landed cost + quality + shipping
6. Adaptive continuous monitoring
7. Self-improving buyer preferences
8. Controlled auto-execution
9. Hybrid free discovery + success fee pricing

### Most Dangerous Combinations (All Models Agreed)
| Threat | Combination | Why It Matters |
|--------|------------|----------------|
| **Consumer** | Rocket Money + Honey/Capital One Shopping | Bank data + product matching |
| **SMB** | Ramp + AI procurement | Transaction data + vendor relationships |
| **Enterprise** | Coupa/Zip + Arkestro/Fairmarkit | Spend visibility + autonomous sourcing |
| **Non-Software** | Expense consultant + better automation | Category expertise + proven success-fee model |

### Recommended Market Wedge (All Models Agreed)
**Recurring physical operating supplies for small businesses**
- Shipping/packaging, office consumables, janitorial, restaurant disposables, facility maintenance, printer supplies
- Why: Repeat purchases, structured specs, material savings, underserved by enterprise tools

---

## 7. Model-by-Model Strengths & Weaknesses

### DeepSeek
**Strengths:**
- Most detailed auction/secondhand pricing prediction model
- Comprehensive JSON schema for research briefs
- Excellent TCO and cross-validation approaches
- Strong "negotiate instead" feature concept

**Weaknesses:**
- Less emphasis on UI/UX design
- No "friction/risk" degradation index
- Missing source authority weighting

### Gemini (Session 1)
**Strengths:**
- Best multi-agent architecture (Scout/Evaluator/Analyst)
- Innovative carrying cost of capital overlay
- Excellent friction/risk degradation index (green/yellow/red)
- Strong Monte Carlo sensitivity analysis

**Weaknesses:**
- OPFS approach less robust than local Rust SQLite
- Less detail on auction/secondhand logic
- Missing source authority weighting

### Gemini (Session 2)
**Strengths:**
- Best competitive battlecard and positioning
- Most complete monetization architecture (floor/ceiling/tiers)
- Strong "buyer memory cache" concept
- Excellent visual savings loop design

**Weaknesses:**
- Some overlap with Session 1 (could be consolidated)
- Less technical depth on the comparison engine itself

### Kimi
**Strengths:**
- Most complete and production-ready architecture
- Full 8-dimension rubric with concrete examples
- Detailed data source tiers (APIs, scraping, trust data)
- Excellent learning loop and preference vector design
- Complete code pseudocode for Rust sandbox
- Best "should cost" analysis framework

**Weaknesses:**
- No Monte Carlo sensitivity analysis
- Less emphasis on competitive positioning
- Missing source authority weighting

### Arena (Claude Sonnet)
**Strengths:**
- Best competitive landscape analysis
- Strong "blue ocean" positioning argument
- Excellent moat strategy recommendations
- Good threat matrix with severity levels

**Weaknesses:**
- Less technical architecture detail
- More strategic than tactical
- Brand name "ExpenseIQ" diverges from "Sparrow"

### SparrowApp.md
**Strengths:**
- Strong design narrative ("Vendor X reduces landed cost by 12%")
- Good efficiency scheduling concepts
- Solid data hygiene principles

**Weaknesses:**
- Shortest and least detailed
- Lacks specific technical architecture
- No competitive analysis

---

## 8. Recommended Consolidated Architecture

Based on the best ideas from all models, here is the recommended Sparrow architecture:

### Core Engine
1. **Local Rust/Tauri App** (all models agree)
2. **Encrypted SQLite** (Gemini 2 + Kimi) — not OPFS
3. **PII Scrubber** (all models) — context-aware, not paranoid
4. **Research Sandbox** (DeepSeek + Kimi) — Firecracker microVM per job

### Multi-Agent System (Gemini 1)
1. **Scout Agent** — discovers alternatives across 3 tiers of sources
2. **Evaluator Agent** — applies 8-dimension rubric (Kimi)
3. **Analyst Agent** — calculates delta, generates report

### Comparison Rubric (Kimi + DeepSeek + Gemini 2)
1. Unit Price (25%) — with bulk discount detection
2. Shipping & Freight (15%) — real-time carrier API
3. Quality Score (20%) — NLP review sentiment + source authority weighting
4. Speed & Reliability (10%) — lead time + stock availability
5. Total Landed Cost (15%) — price + shipping + tax + duties
6. Supplier Trust (8%) — BBB, complaint resolution, years in business
7. Compatibility Risk (5%) — spec matching confidence
8. Sustainability (2%) — eco-certifications

### Advanced Features (Gemini 2 + DeepSeek)
- **Progressive Scraping Funnel** (85% cost reduction)
- **Mock Checkout Verification** (eliminates false positives)
- **Monte Carlo Sensitivity Analysis** ("If Price vs. Speed")
- **Carrying Cost of Capital** (inventory holding friction)
- **Friction Index** (green/yellow/red execution complexity)
- **Confidence Filter** (statistical confidence intervals)
- **What-If Builder** (real-time variable adjustment)

### Secondhand/Auction (DeepSeek + Kimi)
- **Condition Grading Scale** (7 levels)
- **Auction Price Prediction** (historical data + acceleration curve)
- **Risk Penalty Multipliers** (-10% refurbished, -15% auction)
- **User Warning System** (cross-reference with past returns)

### Monetization (DeepSeek + Gemini 2)
- **Free Discovery** (always free)
- **Verification Fee** ($5 for deep dive, waived for Premium)
- **Success Fee** (0.5% individual, 1.5% business)
- **Minimum Fee** ($2 floor)
- **Cap** ($2,500 per optimization)
- **Premium Tier** ($99/mo, auto-execution enabled)

### Learning & Adaptation (All Models)
- **Preference Vector** (on-device, local embeddings)
- **Implicit Learning** (accept/reject patterns)
- **Category Playbooks** (domain-specific checklists)
- **Community Benchmarking** (opt-in, anonymized, zero-knowledge proofs)

---

## 9. Discussion Points

1. **Which model's architecture should be the primary reference?** Kimi is most complete technically, but Gemini's multi-agent approach is elegant.

2. **Monetization model consensus?** DeepSeek's hybrid model (free discovery + paid verification + success fee) seems most balanced.

3. **Rubric dimensions?** Kimi's 8-dimension model is the most comprehensive. Should we adopt all 8 or simplify?

4. **Secondhand/auction logic?** DeepSeek's auction price prediction is the most sophisticated. Kimi's toggle system is the most user-friendly.

5. **Competitive positioning?** All models agree on the "blue ocean" thesis. The recommended wedge (SMB operating supplies) is universally endorsed.

6. **Technical stack?** Local Rust/Tauri with encrypted SQLite is the consensus. OPFS (Gemini 1) is less robust.

7. **Priority features for MVP?** Based on all models: PII scrubber → bank ingestion → category detection → basic comparison → report generation → preference learning → advanced features.
