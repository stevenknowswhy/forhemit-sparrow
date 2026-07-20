# 🐦 Sparrow — Local-First AI Expense Reduction Agent

> **Buy the same thing. Spend less.**

Sparrow is a privacy-first, autonomous buying agent that turns the expenses you already have into clear, evidence-backed ways to spend less. It searches the web for real-time pricing, scores products across 8 transparent dimensions, and generates comparison reports — all running locally on your machine.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Sparrow Ecosystem                     │
├──────────────────┬──────────────────┬───────────────────┤
│  Marketing Site  │   Desktop App    │   Agent Backend   │
│  (Next.js)       │  (Tauri/Rust)    │   (Python)        │
│                  │                  │                   │
│  • Landing page  │  • Product input │  • Brave Search   │
│  • Waitlist form │  • Report viewer │  • 8-dim scorer   │
│  • Pricing       │  • History       │  • Report gen     │
│  • Privacy       │                  │  • LLM analysis   │
├──────────────────┴──────────────────┴───────────────────┤
│                    External Services                     │
│  Brave Search API  │  Agnes AI / OpenRouter  │  FormBricks│
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Run the Agent (Backend)

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn[standard]

# Configure API keys
cp .env.example .env  # then edit with your keys

# Run the HTTP server
python3 server.py
```

### 2. Open the Desktop App

```bash
cd sparrow-app
# The Tauri app loads the frontend from src/index.html
# It connects to the Python agent at http://127.0.0.1:8765
```

### 3. Visit the Marketing Site

```bash
cd marketing-site
npm install
npm run dev
# Opens at http://localhost:3000
```

## The 8-Dimension Rubric

Every product is scored across these dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Price | 25% | Total cost of ownership |
| Quality | 20% | Ratings, reviews, specs |
| Shipping Speed | 15% | Delivery time + free shipping |
| Trust | 15% | Vendor reputation, warranty |
| Warranty | 10% | Coverage length, terms |
| Sustainability | 5% | Eco-friendliness |
| Secondhand | 5% | Refurbished condition grade |
| Preference | 5% | User priority alignment |

📖 **[Read the full rubric docs](agent/docs/rubric.md)**

## Privacy

Sparrow is **local-first**:
- Your search queries stay on your device
- Reports are saved as local HTML files
- Only product data (not personal data) is sent to Brave Search
- No cloud storage, no analytics, no tracking

🔒 **[Read the full privacy policy](sparrow-app/PRIVACY_POLICY.md)**

## Project Structure

```
ForhemitSparrow/
├── agent/                    # Python agent backend
│   ├── agent.py              # LangChain multi-provider agent
│   ├── config.py             # API key configuration
│   ├── run.py                # End-to-end pipeline
│   ├── scorer.py             # 8-dimension rubric engine
│   ├── server.py             # FastAPI HTTP server
│   ├── tools.py              # Brave Search API client
│   └── report_generator.py   # HTML report generator
├── sparrow-app/              # Rust/Tauri desktop app
│   ├── src/                  # Frontend HTML/JS
│   ├── src-tauri/            # Rust backend
│   ├── PRIVACY_POLICY.md     # App privacy policy
│   └── README.md             # Desktop app docs
├── marketing-site/           # Next.js marketing site
│   ├── src/app/              # Pages (home, pricing, waitlist, etc.)
│   └── src/components/       # React components
└── BrainStormThreads/        # Design docs and research
    ├── MERGED_ARCHITECTURE.md
    ├── DEEP_RESEARCH_SPEC.md
    └── COMPARISON_REPORT.md
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Marketing Site | Next.js 16, React 19, Tailwind CSS, Astryx UI |
| Desktop App | Rust, Tauri v2, HTML/CSS/JS |
| Agent Backend | Python 3.14, LangChain, FastAPI, Uvicorn |
| Search | Brave Search API |
| LLM | Agnes AI (primary), OpenRouter (fallback) |
| Surveys | FormBricks |
| Deployment | Vercel (marketing site) |

## License

MIT © Stefano Stokes / Forhemit Sparrow

## Links

- **Website:** [onestarcfo.com](https://onestarcfo.com)
- **Waitlist:** [onestarcfo.com/waitlist](https://onestarcfo.com/waitlist)
- **Privacy:** [onestarcfo.com/privacy](https://onestarcfo.com/privacy)
