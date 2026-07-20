# Sparrow Deep Research Feature — Specification

**Version:** 1.0  
**Date:** July 20, 2026  
**Purpose:** Define the architecture, data sources, and workflow for global product search across all available sources

---

## 1. Problem Statement

The current Scout Agent searches a limited set of sources (Amazon, Google Shopping, eBay, B&H). For complex or niche products, this coverage is insufficient. The Deep Research feature expands search to **globally** — covering structured APIs, AI-native search, SERP scraping, semantic discovery, and specialized marketplaces — so the agent can find *every* viable alternative for any product, anywhere on the web.

---

## 2. Source Categories (Expanded from 3 to 7)

### Tier 0: Product Catalog APIs (Structured, AI-Ready)
| API | Coverage | Cost | Best For |
|-----|----------|------|----------|
| **Channel3** | 100M+ products, 25K+ brands | $7/1K queries (1K free) | Shopping agents — structured products, real prices, buy links, built-in commission |
| **BuyWhere** | Southeast Asia markets | Free tier | Regional multi-market comparison |
| **ReefAPI** | Europe (Geizhals, Cimri, Akakçe) | 4 credits/compare | European price comparison |
| **DataForSEO Ecommerce** | Multi-platform | $15+/mo | Bulk eCommerce data |
| **EcomSource** | Barcode/UPC lookup | Free tier | Product identification from SKU |

### Tier 1: Google Shopping & SERP APIs
| API | Coverage | Cost | Best For |
|-----|----------|------|----------|
| **SerpAPI** | 40+ search engines | $75+/5K searches | Enterprise-grade SERP reliability |
| **Serper** | Google SERP | $0.29–$1.00/1K | Budget-friendly Google access |
| **Bright Data** | Google Shopping scraper | Enterprise | Deep product data extraction |
| **Oxylabs** | Google Shopping scraper | Enterprise | Competitive intelligence |
| **Socialcrawl** | Google Shopping | Per-query | Product detail fetching |
| **SearchApi** | Google Shopping | Per-query | Natural language product queries |
| **Scrape.do** | Google Shopping | Per-query | Lightweight shopping search |

### Tier 2: AI-Native Search APIs
| API | Coverage | Cost | Best For |
|-----|----------|------|----------|
| **Firecrawl** | Full web + content extraction | $83/100K credits | Search → Scrape → Extract in one pipeline. 94% token reduction vs raw HTML. |
| **Exa** | Semantic/neural search | $1.50–$7/1K searches | Research-heavy semantic discovery. Trained on link prediction. |
| **Tavily** | Source-first discovery | $8/1K PAYG | AI search with source credibility. LangChain/LlamaIndex integration. |
| **Parallel AI** | Evidence-backed research | $0.005/10 results | Enterprise research with provenance. 47% HLE benchmark accuracy. |
| **Perplexity Sonar** | Web-grounded LLM answers | $1/1M tokens + $5–14/1K | Citation-ready answers out of the box. |
| **Brave Search** | 30B+ pages, independent index | $5/1K queries | Privacy-first, Google-independent search. SOC 2 Type II. |

### Tier 3: Web Scraping Infrastructure
| Tool | Type | Cost | Best For |
|------|------|------|----------|
| **Apify** | Actor marketplace | $49+/mo | eBay, Amazon, Shopify actors |
| **Firecrawl** | Scrape + Crawl + Interact | Included above | JS rendering, anti-bot, proxy rotation |
| **Bright Data** | Proxy + Scraping | Enterprise | Scale, reliability, anti-bot bypass |
| **Browserbase/Stagehand** | Headless browser | $40+/mo | CDP-native, no Playwright dependency |
| **Crawl4AI** | Open-source crawler | Free (self-host) | Self-hosted, privacy-first |
| **MoClaw** | AI scraping agent | TBD | Autonomous scraping with LLM reasoning |

### Tier 4: Specialized Marketplaces
| Source | Coverage | Access Method |
|--------|----------|--------------|
| **eBay API** | Auctions, used, refurbished | Official API (5K calls/day free) |
| **Amazon PAA** | New, used, renew, warehouse | Official API (affiliate required) |
| **Walmart API** | Marketplace, grocery, general | Official API (free) |
| **Best Buy API** | Electronics, open-box | Official API (free) |
| **Google Shopping** | Multi-retailer | SERP API or native |
| **B-Stock** | Liquidation, returns, overstock | API / scraping |
| **Liquidation.com** | Bulk lots, pallets | API / scraping |
| **GovDeals** | Government surplus | API / scraping |
| **Back Market** | Certified refurbished | API / scraping |
| **AliExpress** | Wholesale, direct from China | API / scraping |
| **Alibaba** | B2B wholesale | API / scraping |

### Tier 5: Quality & Trust Data
| Source | Data | Access |
|--------|------|--------|
| **ReviewMeta / Fakespot** | Review authenticity scores | API |
| **BBB.org** | Business ratings, complaints | Scraping |
| **Trustpilot** | Seller ratings, volume | API |
| **Keepa** | Amazon price history | API ($99+/mo) |
| **CamelCamelCamel** | Amazon price history | Free API |
| **Reddit / Forums** | Real user experiences, defects | Scraping |

### Tier 6: Agentic Commerce Protocols (Emerging 2026)
| Protocol | Description | Status |
|----------|-------------|--------|
| **Google UCP** | Universal Commerce Protocol — AI agents discover, compare, checkout | Beta, 2.35B Apple devices |
| **OpenAI ACP** | Agentic Commerce Protocol — standardized product feeds and checkout | Early |
| **Structured Context API** | AI-optimized product metadata for agent consumption | Emerging |

---

## 3. Deep Research Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEEP RESEARCH ORCHESTRATOR                   │
│                                                                 │
│  Step 1: QUERY EXPANSION                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Input: "HP 64A toner cartridge"                          │  │
│  │ → Extract specs (SKU, yield, compatibility)               │  │
│  │ → Generate 8–12 search variants:                           │  │
│  │   • "HP CC364A toner"                                      │  │
│  │   • "HP 64A compatible black"                              │  │
│  │   • "HP LaserJet P4015 toner"                              │  │
│  │   • "CC364A remanufactured"                                │  │
│  │   • "HP 64A bulk wholesale"                                │  │
│  │   • "HP 64A refurbished"                                   │  │
│  │   • "HP 64A auction"                                       │  │
│  │   • "toner cartridge P4014 P4015 P4515"                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Step 2: PARALLEL DISPATCH (7 tiers)                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ Tier 0   │ Tier 1   │ Tier 2   │ Tier 3   │ Tier 4   │    │
│  │ Catalog  │ SERP     │ AI Search│ Scrape   │ Special  │    │
│  │ APIs     │ APIs     │ APIs     │ Infra    │ Markets  │    │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
│       ↓          ↓          ↓          ↓          ↓           │
│  Channel3   SerpAPI    Firecrawl  Apify    eBay API          │
│  BuyWhere   Serper     Exa       Bright   Amazon PAA          │
│  ReefAPI    Brave      Tavily    Browser  Best Buy            │
│             Google     Parallel  Base     Back Market          │
│                          Shopping                 Keepa         │
│                                                                 │
│  Step 3: RESULT NORMALIZATION                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ All results → ProductFingerprint {                       │  │
│  │   sku, brand, category, price, shipping, rating,         │  │
│  │   seller, condition, warranty, stock, url, image          │  │
│  │ }                                                         │  │
│  │ Deduplication: hash by (sku + brand + price ± 5%)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Step 4: QUALITY FILTERING                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Remove:                                                   │  │
│  │   • Results with < 3 data points                          │  │
│  │   • Results missing price or shipping                     │  │
│  │   • Results from unverified sellers (no rating)           │  │
│  │ Keep:                                                     │  │
│  │   • Top 15–25 unique products                             │  │
│  │   • Mix of new, refurbished, auction                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Step 5: RUBRIC EVALUATION (8 dimensions)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Evaluator Agent scores each of the 15–25 products         │  │
│  │ on the full 8-dimension rubric                            │  │
│  │ → Ranked list with scores                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Step 6: ANALYST SYNTHESIS                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Analyst Agent generates:                                  │  │
│  │   • Executive summary                                     │  │
│  │   • Top 3 recommendations                                 │  │
│  │   • What-if scenarios                                     │  │
│  │   • Confidence assessment                                 │  │
│  │   • Source provenance                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Step 7: OUTPUT                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Full report (HTML/CSS) + JSON + CSV export                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Query Expansion Engine

Before any search runs, the agent expands the input into multiple search variants:

```rust
// Pseudo-code for query expansion
pub struct QueryExpander {
    product: ProductFingerprint,
}

impl QueryExpander {
    pub fn expand(&self) -> Vec<SearchVariant> {
        vec![
            SearchVariant {
                query: format!("{} {}", self.product.brand, self.product.sku),
                priority: 1,
                source_tiers: [0, 1, 2],
            },
            SearchVariant {
                query: format!("{} compatible {} toner", self.product.brand, self.product.model),
                priority: 2,
                source_tiers: [0, 1, 2, 4],
            },
            SearchVariant {
                query: format!("{} {} refurbished", self.product.brand, self.product.sku),
                priority: 3,
                source_tiers: [4],
            },
            SearchVariant {
                query: format!("{} {} auction", self.product.brand, self.product.sku),
                priority: 4,
                source_tiers: [4],
            },
            SearchVariant {
                query: format!("{} {} bulk wholesale", self.product.brand, self.product.sku),
                priority: 5,
                source_tiers: [0, 1, 2, 4],
            },
            SearchVariant {
                query: format!("toner cartridge for {}", self.product.compatible_printers[0]),
                priority: 6,
                source_tiers: [0, 1, 2],
            },
        ]
    }
}
```

---

## 5. API Selection Matrix

### Which API to Use When

| Scenario | Primary API | Fallback |
|----------|------------|----------|
| **Common product, broad search** | Channel3 (Tier 0) | SerpAPI (Tier 1) |
| **Niche product, no catalog match** | Firecrawl (Tier 2) | Brave Search (Tier 2) |
| **Deep semantic research** | Exa (Tier 2) | Tavily (Tier 2) |
| **Enterprise-grade evidence** | Parallel AI (Tier 2) | Perplexity Sonar (Tier 2) |
| **Price monitoring / history** | Keepa API | CamelCamelCamel |
| **eBay/auction data** | eBay API | Apify eBay Actor |
| **European products** | ReefAPI | Google Shopping (via SerpAPI) |
| **Southeast Asia** | BuyWhere | Google Shopping |
| **Privacy-first search** | Brave Search | Exa |
| **Bulk product lookup** | DataForSEO | Scrape.do |

### Cost Optimization Strategy

```
Phase 1: Tier 0 (Catalog APIs) — cheapest, most structured
  → If results found → STOP (use these)
  
Phase 2: Tier 1 (SERP APIs) — moderate cost, broad coverage
  → If results found → STOP (use these)
  
Phase 3: Tier 2 (AI Search APIs) — higher cost, deeper coverage
  → If results found → STOP (use these)
  
Phase 4: Tier 3 (Scraping) — most expensive, last resort
  → Only for products not found in any structured source
  
Phase 5: Tier 4 (Specialized Markets) — conditional
  → Only if user toggled secondhand/auction ON
```

This progressive approach ensures we spend the **minimum necessary** to find good results.

---

## 6. Deduplication & Normalization

Products from different sources often represent the same item:

```rust
// Deduplication by fuzzy matching
pub struct ProductNormalizer {
    raw_products: Vec<RawProduct>,
}

impl ProductNormalizer {
    pub fn deduplicate(&self) -> Vec<ProductFingerprint> {
        // Group by:
        // 1. Exact SKU match
        // 2. Brand + model similarity (Levenshtein distance < 2)
        // 3. Price ± 5% + same specs
        // 4. EAN/GTIN match (if available)
        
        // Keep the best-priced variant from each group
        // Flag cross-retailer options for the same product
    }
}
```

---

## 7. Search Budget & Rate Limits

### Per-Research Session Budget

| Component | Max Cost | Max Time |
|-----------|----------|----------|
| Tier 0 (Catalog APIs) | $0.05 | 2 seconds |
| Tier 1 (SERP APIs) | $0.15 | 5 seconds |
| Tier 2 (AI Search) | $0.20 | 5 seconds |
| Tier 3 (Scraping) | $0.30 | 15 seconds |
| Tier 4 (Specialized) | $0.10 | 3 seconds |
| **Total per research** | **~$0.80** | **~30 seconds** |

### Rate Limiting

| API | Rate Limit | Burst |
|-----|-----------|-------|
| Channel3 | 100/min | 20 burst |
| SerpAPI | 50/min | 10 burst |
| Firecrawl | 60/min | 12 burst |
| Exa | 100/min | 20 burst |
| Brave | 150/min | 30 burst |
| eBay API | 5,000/day free | N/A |
| Keepa | 100/min | 20 burst |

---

## 8. MCP Integration

For the live agent (running in the current session), we use MCP servers:

| MCP Server | Purpose | Setup |
|-----------|---------|-------|
| **Firecrawl MCP** | Search + scrape + crawl + interact | Remote-hosted, 13 tools |
| **Brave Search MCP** | Privacy-first web search | Remote-hosted |
| **Exa MCP** | Semantic research search | Local process |
| **Perplexity Sonar MCP** | Grounded LLM answers | OpenAI-compatible |
| **Serper MCP** | Google search results | TypeScript-based |
| **BuyWhere MCP** | Southeast Asia product search | Node.js-based |

---

## 9. Deep Research Report Enhancements

When Deep Research is enabled, the report adds:

### New Sections
1. **Coverage Summary** — How many sources searched, how many products found
2. **Cross-Retailer Options** — Same product available from multiple vendors
3. **Regional Variants** — Products available in different regions/currencies
4. **Price History** — Keepa/CamelCamelCamel trend for key alternatives
5. **Supply Chain Risk** — Geographic concentration, single-source dependencies
6. **Market Depth** — How many alternatives exist (thin = risky, deep = safe)

### New Metrics
| Metric | Description |
|--------|-------------|
| **Source Diversity** | How many different API tiers found results |
| **Price Spread** | Range between cheapest and most expensive |
| **Market Saturation** | Number of unique products found |
| **Geographic Coverage** | Countries/regions represented |
| **Channel Diversity** | New, refurbished, auction, wholesale mix |

---

## 10. Implementation Priority

### Phase 1: Immediate (Week 1–2)
- [ ] Integrate Channel3 API (Tier 0) — best ROI, structured data
- [ ] Integrate SerpAPI Google Shopping (Tier 1) — broad coverage
- [ ] Add Brave Search MCP (Tier 2) — free tier, privacy-first
- [ ] Implement query expansion engine
- [ ] Add deduplication logic

### Phase 2: Near Term (Week 3–4)
- [ ] Integrate Firecrawl MCP (Tier 2) — search + scrape pipeline
- [ ] Integrate Exa MCP (Tier 2) — semantic search
- [ ] Add Keepa API for price history
- [ ] Implement progressive tier fallback
- [ ] Add coverage summary to report

### Phase 3: Advanced (Month 2)
- [ ] Integrate Apify actors (Tier 3) — eBay, Amazon scraping
- [ ] Add ReefAPI for European coverage (Tier 0)
- [ ] Integrate BuyWhere for SEA coverage (Tier 0)
- [ ] Add supply chain risk scoring
- [ ] Implement market depth analysis

### Phase 4: Future (Month 3+)
- [ ] Monitor Google UCP rollout (Tier 6)
- [ ] Monitor OpenAI ACP rollout (Tier 6)
- [ ] Add visual search (image-to-product)
- [ ] Implement autonomous multi-step research (Parallel AI Task API)
- [ ] Add real-time price monitoring alerts

---

*This spec defines a comprehensive deep research feature that expands Sparrow's search from ~10 sources to 50+ sources across 7 tiers, with intelligent query expansion, progressive fallback, deduplication, and cost optimization.*
