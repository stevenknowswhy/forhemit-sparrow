# Sparrow — Agent Handoff

## Project
A product comparison/scoring pipeline that searches for office supplies across vendors, extracts metadata from search results, scores them against configurable rubrics, and produces HTML reports. Local-first: no external DB, filesystem-backed.

## Architecture

```
agent/
├── tools.py            # Search backend abstraction (Serper → Tavily → Brave → stub)
├── run.py              # CLI pipeline: search → extract → score → report
├── scorer.py           # Rubric presets (consumer, business), scoring functions
├── extractor.py        # Regex-based price/rating/shipping extraction from text
├── settings.py         # User preference persistence (user_settings.json)
├── server.py           # FastAPI server with /compare, /rubrics, /settings endpoints
├── report_generator.py # HTML report rendering with confidence indicators
├── .env                # API keys (gitignored)
├── requirements.txt
└── BrainStormThreads/MERGED_ARCHITECTURE.md  # Design docs & business rubric spec
```

## Design Documents (BrainStormThreads/)

| File | Relevance |
|------|-----------|
| `MERGED_ARCHITECTURE.md` | **Approved architecture spec.** Covers 3-agent pattern (Scout/Evaluator/Analyst), 8-dimension rubric with formulas, business rubric weights (lines 173-186), MVP roadmap (Phase 1-5), monetization tiers, secondhand logic. The canonical design reference. |
| `DEEP_RESEARCH_SPEC.md` | **Multi-source search spec.** 7 tiers of data sources. We cover Tier 1 (Serper for Google Shopping), Tier 2 (Tavily for AI-native), and Tier 3 (Brave). Still missing: Amazon PA API, eBay API, Walmart API, product page scraping. |
| `REPORT_TEMPLATE_DESIGN.md` | **CFO Pro Buyer report design.** 7-section spec (Hero, Comparison Table, Dimension Breakdown, What-If, Secondhand, Sources, Edge Case). Current `report_generator.py` is simpler — consider updating to match. |
| `ASTRYX_COMPONENTS_PLAN.md` | **UI component map.** Maps Astryx design system to report layout. Relevant for `sparrow-app/` (Tauri) or `marketing-site/` (Next.js). |
| `LIVE_VS_SPEC_TEST.md` | **A/B test: live search vs spec.** Earlier test comparing real Brave Search output vs hand-written spec. Shows the gap live search had before Serper. |
| `rubric.md` (in `agent/docs/`) | **Consumer 8-dim rubric docs.** Covers scoring formulas — but only for consumer preset. Business preset not documented here yet. |

## MVP Roadmap (from MERGED_ARCHITECTURE.md)

The approved spec defines 5 phases. Our Python agent covers parts of **Phase 2** (research engine, scoring, report generation) but in Python, not Rust. The Tauri app (`sparrow-app/`) is the intended Phase 3 delivery vehicle.

**What we have** (Python agent): Phase 2 search + scoring + HTML reports, but as CLI/server not Tauri.
**What's still needed** (Rust/Tauri app at `sparrow-app/`): Phase 1 (core scaffold, SQLite, PII scrubber, Excel parser), Phase 3 (Tauri frontend, invoke/reject flow, savings ledger), Phase 4 (preference learning, adaptive scheduling, auction logic).

## Search Backend Priority
1. **Serper.dev** (`/shopping` endpoint) — 40 results/query with structured prices, ratings, ratingCount, vendor name. Activated via `SERPER_API_KEY`.
2. **Walmart Marketplace API** (`/v3/items/search`) — Structured product data with prices, stock status, ratings. OAuth2 client credentials. Activated via `WALMART_CLIENT_ID` + `WALMART_CLIENT_SECRET`. Free tier available.
3. **Best Buy API** (`/v1/products`) — Structured prices, ratings, `freeShipping` flag, in-store/online availability. Simple API key auth. Activated via `BESTBUY_API_KEY`. Free tier available.
4. **Tavily** (`/search`) — AI-native search, returns 2000-char `content` per result. Activated via `TAVILY_API_KEY`. Falls back when Serper returns 0.
5. **Brave Search** (`/web/search`) — General web snippets. Activated via `BRAVE_SEARCH_API_KEY`.
6. **Stub** — Built-in demo data when no API keys set.

## What's Complete
- [x] Serper.dev integration — `/shopping` endpoint returns structured price/rating/review/vendor
- [x] Tavily integration — rich content extraction, `extract_tavily(urls)` for future page scraping
- [x] Brave Search freshness filter removed (was limiting results to 1 week)
- [x] Unified `search()` auto-selects best available backend
- [x] Two rubric presets: Consumer (8 dims) and Business/CFO (7 dims, merged logistics)
- [x] CLI flags: `--rubric`, `--custom-weights`, `--list-rubrics`, `--reference-vendor`
- [x] FastAPI: `GET /rubrics`, `GET /settings`, `PUT /settings`, compare endpoint with rubric/confidence
- [x] Extractor: works on snippet + title + extra_snippets; rating regex handles "4.7Read" format
- [x] Confidence/uncertainty penalty in reports with `data_quality` indicators (● data-backed, ○ default)
- [x] Vendor detection expanded (hp.com, dell.com, lenovo, target, lowes, homedepot, etc.)
- [x] `.env` configured with keys for all three providers: Serper, Tavily, Brave

## Decisions Made
- **Serper over Tavily for primary**: Shopping endpoint returns actual structured prices/ratings. Tavily's richer content helps the extractor on fallback but can't match structured data.
- **No product page scraping yet**: Serper shopping data covers prices + ratings. Shipping/warranty gaps remain but require per-page scraping or LLM extraction.
- **Single-agent pipeline**: Two-agent + judge reliability pass deferred; current architecture is simple and fast enough.
- **Python first, Rust later**: MVP roadmap calls for Rust/Tauri, but rapid prototyping in Python was faster. The `sparrow-app/` directory has the Tauri scaffold ready.

## Data Gaps (still default to 50)
- Shipping speed / shipping cost
- Vendor reputation / trust scores (Trustpilot, BBB)
- Warranty coverage length
- Sustainability certifications

These aren't available from Google Shopping or web snippets. The DEEP_RESEARCH_SPEC.md lists dedicated APIs and scraping targets for each.

## Open Items / Next Moves
1. **Fill remaining data gaps**: Shipping speed, vendor reputation, warranty, sustainability still default to 50. Options:
   - Scrape product pages with Tavily extract or Playwright for structured data (JSON-LD/meta tags)
   - LLM extraction pass over Tavily's rich `content` field to find shipping/warranty mentions
   - Add dedicated APIs (Free: Amazon PA, eBay, Walmart)
   - Accept as-is (most comparison tools also lack this data)
2. **Two-agent judge pass**: Add a validation agent that cross-checks scores for consistency
3. **Tauri desktop app** (`sparrow-app/`): File picker for running reports locally, notification on completion
4. **More rubric presets**: Add "IT Procurement" or "Freight Forwarder" presets
5. **Report improvements**: Update report_generator.py to match REPORT_TEMPLATE_DESIGN.md spec (7 sections, What-If scenarios, Edge Cases)
6. **Update rubric docs**: agent/docs/rubric.md only documents consumer preset — business preset is missing from docs

## Running
```bash
cd agent
source venv/bin/activate
python run.py "HP 64A toner"                      # Consumer rubric (default)
python run.py "HP 64A toner" --rubric business     # Business rubric
python run.py --list-rubrics                        # List presets
uvicorn server:app --port 7860                      # API server
```
