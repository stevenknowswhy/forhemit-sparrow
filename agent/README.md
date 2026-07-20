# Sparrow — Local-First AI Expense Reduction Agent

🐦 **Buy the same thing. Spend less.**

Sparrow is a privacy-first, autonomous buying agent that searches the web, scores products across 8 transparent dimensions, and generates evidence-backed comparison reports — all running locally on your machine.

---

## Quick Start

### Prerequisites

- Python 3.12+ (recommended: use the bundled virtual environment)
- Brave Search API key (free tier: 2,000 queries/month)
- Agnes AI or OpenRouter API key (for LLM-powered analysis)

### Installation

```bash
cd agent
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install fastapi uvicorn[standard]
```

### Configure API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:
```
BRAVE_SEARCH_API_KEY=your_brave_key_here
AGNES_API_KEY=your_agnes_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

### Run the Agent

**Option 1: Interactive REPL**
```bash
python3 main.py
```

**Option 2: Pipeline Runner**
```bash
python3 run.py "HP 64A toner cartridge"
```

**Option 3: Desktop App (HTTP Server)**
```bash
python3 server.py
```
Then open the Tauri desktop app (`sparrow-app/`) to interact via GUI.

---

## How It Works

1. **Search** — Sparrow uses Brave Search to find real-time product listings, prices, and vendor information.
2. **Score** — Each product is evaluated across 8 dimensions (see below).
3. **Report** — A styled HTML comparison report is generated with rankings, savings estimates, and source citations.

## The 8-Dimension Rubric

Sparrow evaluates every product on a standardized rubric:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Price** | 25% | Total cost of ownership — lower is better |
| **Quality** | 20% | Product ratings, review count, specs |
| **Shipping Speed** | 15% | Delivery time + free shipping bonus |
| **Trust** | 15% | Vendor reputation, Trustpilot, warranty |
| **Warranty** | 10% | Coverage length, terms, ease of claim |
| **Sustainability** | 5% | Eco-friendliness, recyclability, carbon footprint |
| **Secondhand** | 5% | Condition grade for refurbished/open-box items |
| **Preference** | 5% | Alignment with user-specified priorities |

Scores are normalized to 0–100 and weighted. The total score determines the ranking.

See [`docs/rubric.md`](docs/rubric.md) for detailed scoring algorithms.

---

## Privacy

Sparrow is **local-first**. Your search queries, comparison results, and personal preferences never leave your machine unless you explicitly share a report. The only external calls are:

- **Brave Search API** — for product data (no personal data sent)
- **LLM Provider** — for qualitative analysis (queries are anonymized)

No data is stored on cloud servers. Reports are saved locally as HTML files.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Tauri App  │────▶│  FastAPI     │────▶│  Brave      │
│  (Frontend) │◀────│  Server      │◀────│  Search API │
└─────────────┘     │  (:8765)     │     └─────────────┘
                    │              │
                    │  ┌─────────┐ │
                    │  │  Agent  │ │
                    │  │ Pipeline│ │
                    │  └─────────┘ │
                    │     │        │
                    │     ▼        │
                    │  ┌─────────┐ │
                    │  │  Scorer │ │
                    │  │(8-dim)  │ │
                    │  └─────────┘ │
                    │     │        │
                    │     ▼        │
                    │  ┌─────────┐ │
                    │  │ Reporter│ │
                    │  │ (HTML)  │ │
                    │  └─────────┘ │
                    └──────────────┘
```

---

## License

MIT © Stefano Stokes / Forhemit Sparrow

---

## Support

- **Website:** [onestarcfo.com](https://onestarcfo.com)
- **Issues:** [GitHub Issues](https://github.com/ForhemitSparrow/sparrow/issues)
- **Contact:** [onestarcfo.com/contact](https://onestarcfo.com/contact)
