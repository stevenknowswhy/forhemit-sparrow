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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models for the API
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    query: str
    rubric: str | None = None
    reference_vendor: str | None = None

class CompareResponse(BaseModel):
    status: str
    query: str
    report_path: str | None = None
    report_url: str | None = None
    products_found: int = 0
    scores: list[dict] | None = None
    savings: dict | None = None
    rubric: str | None = None
    rubric_label: str | None = None
    error: str | None = None

class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"

class SettingsResponse(BaseModel):
    rubric: str
    rubric_label: str
    custom_weights: dict | None
    available_rubrics: list[dict]

class SettingsUpdateRequest(BaseModel):
    rubric: str | None = None
    custom_weights: dict | None = None

class RubricsListResponse(BaseModel):
    rubrics: list[dict]


# ---------------------------------------------------------------------------
# Import the pipeline
# ---------------------------------------------------------------------------

from run import fetch_products, score_from_raw
from scorer import score_batch, get_preset, get_preset_labels, RUBRIC_PRESETS
from report_generator import generate_report
from settings import load_settings, save_settings, get_active_rubric


REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

STATIC_REPORTS_DIR = Path(__file__).parent / "static_reports"
STATIC_REPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Sparrow Agent",
    description="Local-first AI expense reduction agent API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/rubrics", response_model=RubricsListResponse)
async def list_rubrics():
    rubrics = []
    for key, preset in RUBRIC_PRESETS.items():
        rubrics.append({
            "id": key,
            "label": preset["label"],
            "description": preset["description"],
            "dimensions": [
                {"key": k, "label": v["label"], "weight": v["weight"]}
                for k, v in preset["dimensions"]
            ],
        })
    return {"rubrics": rubrics}


@app.get("/settings", response_model=SettingsResponse)
async def get_settings():
    s = load_settings()
    rubric = s.get("rubric", "consumer")
    preset = get_preset(rubric)
    rubrics_list = []
    for key, p in RUBRIC_PRESETS.items():
        rubrics_list.append({
            "id": key,
            "label": p["label"],
            "description": p["description"],
        })
    return SettingsResponse(
        rubric=rubric,
        rubric_label=preset["label"],
        custom_weights=s.get("custom_weights"),
        available_rubrics=rubrics_list,
    )


@app.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest):
    updates = {}
    if req.rubric is not None:
        updates["rubric"] = req.rubric
    if req.custom_weights is not None:
        updates["custom_weights"] = req.custom_weights
    try:
        saved = save_settings(updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rubric = saved.get("rubric", "consumer")
    preset = get_preset(rubric)
    rubrics_list = []
    for key, p in RUBRIC_PRESETS.items():
        rubrics_list.append({"id": key, "label": p["label"], "description": p["description"]})
    return SettingsResponse(
        rubric=rubric,
        rubric_label=preset["label"],
        custom_weights=saved.get("custom_weights"),
        available_rubrics=rubrics_list,
    )


@app.post("/compare", response_model=CompareResponse)
async def compare_products(req: CompareRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    rubric = req.rubric or get_active_rubric()
    if rubric not in RUBRIC_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown rubric '{rubric}'")

    preset_def = get_preset(rubric)
    preset_label = preset_def["label"]

    try:
        raw_products = fetch_products(query)
        products_found = len(raw_products)

        if products_found == 0:
            return CompareResponse(
                status="no_results",
                query=query,
                rubric=rubric,
                rubric_label=preset_label,
                error=f"No products found for '{query}'. Try a different query.",
            )

        scored_inputs = score_from_raw(raw_products, preset=rubric)
        settings = load_settings()
        custom_weights = settings.get("custom_weights")
        weights = custom_weights if custom_weights else None

        if req.reference_vendor:
            ref = next(
                (p for p in scored_inputs if p["vendor"].lower() == req.reference_vendor.lower()),
                None,
            )
            if ref:
                ref_scores = ref.get("scores", {})
                for p in scored_inputs:
                    p["reference_scores"] = ref_scores

        scored = score_batch(scored_inputs, weights=weights)

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

        report_html = generate_report(
            scored=scored,
            product_query=query,
            savings_data=savings_data,
            preset=rubric,
        )

        safe_name = f"{query}_{rubric}".replace(" ", "_").lower()[:50]
        report_filename = f"report_{safe_name}.html"
        report_path = REPORTS_DIR / report_filename
        report_path.write_text(report_html)

        static_path = STATIC_REPORTS_DIR / report_filename
        static_path.write_text(report_html)

        scores_list = []
        for ps in scored:
            dim_map = {d.name: d.score for d in ps.dimensions}
            scores_list.append({
                "rank": ps.rank_in_batch,
                "vendor": ps.vendor,
                "product_name": ps.product_name,
                "total_score": round(ps.total_weighted_score, 1),
                "confidence": round(ps.confidence, 2),
                "data_quality": ps.data_quality,
                "dimensions": dim_map,
                "url": ps.url,
            })

        return CompareResponse(
            status="success",
            query=query,
            rubric=rubric,
            rubric_label=preset_label,
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
    report_file = STATIC_REPORTS_DIR / filename
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_file, media_type="text/html")


# ---------------------------------------------------------------------------
# Run server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("🐦 Sparrow Agent HTTP Server v0.2.0 starting...")
    print("   Endpoint: http://127.0.0.1:8765")
    print("   Compare:  POST /compare  {\"query\": \"HP 64A toner\"}")
    print("   Settings: GET  /settings")
    print("   Settings: PUT  /settings  {\"rubric\": \"business\"}")
    print("   Rubrics:  GET  /rubrics")
    print("   Health:   GET  /health")
    print("   Reports:  GET  /reports/<filename>")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
