"""
Sparrow Agent HTTP Server

Wraps the existing agent pipeline (search → score → report) behind a
local FastAPI HTTP endpoint so the Tauri desktop app can call it via IPC.

Usage:
    cd agent
    source venv/bin/activate
    python3 server.py

Server runs at http://127.0.0.1:8765
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure agent modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models for the API
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    """User submits a product query."""
    query: str


class CompareResponse(BaseModel):
    status: str
    query: str
    report_path: str | None = None
    report_url: str | None = None
    products_found: int = 0
    scores: list[dict] | None = None
    savings: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


# ---------------------------------------------------------------------------
# Import the pipeline (only when server starts)
# ---------------------------------------------------------------------------

from run import fetch_products, score_from_raw
from scorer import score_batch
from report_generator import generate_report


REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Static path for serving reports via HTTP
STATIC_REPORTS_DIR = Path(__file__).parent / "static_reports"
STATIC_REPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background runner loop."""
    yield


app = FastAPI(
    title="Sparrow Agent",
    description="Local-first AI expense reduction agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the Tauri frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri dev server runs on localhost:1420
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check — Tauri frontend calls this to verify the agent is running."""
    return {"status": "ok"}


@app.post("/compare", response_model=CompareResponse)
async def compare_products(req: CompareRequest):
    """
    Run the full pipeline: search → score → report.
    
    This is the main endpoint. The Tauri frontend sends a product query
    here and receives a comparison report in return.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        # Step 1: Fetch products via Brave Search
        raw_products = fetch_products(query)
        products_found = len(raw_products)

        if products_found == 0:
            return CompareResponse(
                status="no_results",
                query=query,
                error=f"No products found for '{query}'. Try a different query.",
            )

        # Step 2: Score products
        scored_inputs = score_from_raw(raw_products)
        scored = score_batch(scored_inputs)

        # Step 3: Calculate savings
        prices = [
            p.get("metadata", {}).get("price", 0)
            for p in scored_inputs
            if isinstance(p.get("metadata", {}).get("price"), (int, float))
        ]
        if prices and len(prices) > 1:
            current_price = max(prices)
            best_price = min(prices)
            annual_savings_val = (current_price - best_price) * 4
            savings_data = {
                "annual_savings": f"{annual_savings_val:.2f}",
                "fee": f"{annual_savings_val * 0.1:.2f}",
                "net_benefit": f"{annual_savings_val * 0.9:.2f}",
            }
        elif prices:
            savings_data = {"annual_savings": str(prices[0]), "fee": "?", "net_benefit": "?"}
        else:
            savings_data = {"annual_savings": "?", "fee": "?", "net_benefit": "?"}

        # Step 4: Generate HTML report
        report_html = generate_report(
            scored=scored,
            product_query=query,
            savings_data=savings_data,
        )

        # Save report
        safe_name = query.replace(" ", "_").lower()[:40]
        report_filename = f"report_{safe_name}.html"
        report_path = REPORTS_DIR / report_filename
        report_path.write_text(report_html)

        # Also copy to static_reports for HTTP serving
        static_path = STATIC_REPORTS_DIR / report_filename
        static_path.write_text(report_html)

        # Build scores list for the frontend
        scores_list = []
        for ps in scored:
            dim_map = {d.name: d.score for d in ps.dimensions}
            scores_list.append({
                "rank": ps.rank_in_batch,
                "vendor": ps.vendor,
                "product_name": ps.product_name,
                "total_score": round(ps.total_weighted_score, 1),
                "dimensions": dim_map,
                "url": ps.url,
            })

        return CompareResponse(
            status="success",
            query=query,
            report_path=str(static_path),
            report_url=f"/reports/{report_filename}",
            products_found=products_found,
            scores=scores_list,
            savings=savings_data,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/reports/{filename}")
async def serve_report(filename: str):
    """Serve a generated HTML report file."""
    report_file = STATIC_REPORTS_DIR / filename
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_file, media_type="text/html")


# ---------------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("🐦 Sparrow Agent HTTP Server starting...")
    print("   Endpoint: http://127.0.0.1:8765")
    print("   Compare:  POST /compare  {\"query\": \"HP 64A toner\"}")
    print("   Health:   GET  /health")
    print("   Reports:  GET  /reports/<filename>")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
