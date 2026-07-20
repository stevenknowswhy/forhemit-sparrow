"""
Product comparison report generator.
Takes scored ProductScore objects and produces a styled HTML report.
"""
from __future__ import annotations
import json
import io
from datetime import datetime, timezone
from typing import Optional

from scorer import ProductScore, format_dimension_breakdown, DIM_LABELS, DIMENSIONS


# ── Color palette (navy blue brand) ────────────────────────────────

CSS = """
:root {
    --navy: #0f172a;
    --navy-light: #1e293b;
    --accent: #059669;
    --accent-light: #10b981;
    --warning: #d97706;
    --danger: #dc2626;
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    --slate-300: #cbd5e1;
    --slate-400: #94a3b8;
    --slate-500: #64748b;
    --slate-600: #475569;
    --white: #ffffff;
    --radius: 8px;
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--slate-100);
    color: var(--navy);
    line-height: 1.6;
    padding: 2rem 1rem;
}

.report-container {
    max-width: 860px;
    margin: 0 auto;
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
    color: var(--white);
    padding: 2.5rem 2rem;
    text-align: center;
}
.hero h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.hero .recommendation {
    font-size: 1.25rem;
    color: var(--accent-light);
    margin-bottom: 1rem;
}
.hero .savings {
    font-size: 2.5rem;
    font-weight: 800;
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--accent-light);
}
.hero .meta {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    color: var(--slate-300);
}
.hero .meta span strong {
    color: var(--white);
}

/* ── Sections ── */
.section {
    padding: 1.5rem 2rem;
    border-bottom: 1px solid var(--slate-200);
}
.section:last-child { border-bottom: none; }
.section h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--navy);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section h2 .icon { font-size: 1.2rem; }

/* ── Comparison Table ── */
.comp-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}
.comp-table th {
    background: var(--slate-50);
    padding: 0.6rem 0.75rem;
    text-align: left;
    font-weight: 600;
    color: var(--slate-600);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--slate-200);
}
.comp-table td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--slate-200);
    vertical-align: top;
}
.comp-table tr.best td {
    background: rgba(5, 150, 105, 0.05);
    border-left: 3px solid var(--accent);
}
.comp-table .score-cell {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-weight: 700;
    font-size: 1rem;
}
.comp-table .score-high { color: var(--accent); }
.comp-table .score-med { color: var(--warning); }
.comp-table .score-low { color: var(--danger); }
.comp-table .price-cell {
    font-family: 'SF Mono', 'Fira Code', monospace;
    white-space: nowrap;
}
.comp-table .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
}
.badge-best { background: var(--accent); color: var(--white); }
.badge-secondhand { background: var(--warning); color: var(--white); }

/* ── Dimension Bars ── */
.dim-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.4rem 0;
    font-size: 0.85rem;
}
.dim-label {
    flex: 0 0 180px;
    color: var(--slate-600);
}
.dim-bar-bg {
    flex: 1;
    height: 12px;
    background: var(--slate-200);
    border-radius: 6px;
    overflow: hidden;
}
.dim-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.3s;
}
.dim-score {
    flex: 0 0 40px;
    text-align: right;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-weight: 600;
    font-size: 0.8rem;
}

/* ── Scenario Cards ── */
.scenarios {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
}
.scenario-card {
    background: var(--slate-50);
    border: 1px solid var(--slate-200);
    border-radius: var(--radius);
    padding: 1rem;
}
.scenario-card h3 {
    font-size: 0.85rem;
    color: var(--slate-500);
    margin-bottom: 0.3rem;
}
.scenario-card .pick {
    font-weight: 700;
    font-size: 1rem;
    color: var(--navy);
}
.scenario-card .why {
    font-size: 0.8rem;
    color: var(--slate-500);
    margin-top: 0.25rem;
}

/* ── Sources ── */
.source-item {
    display: flex;
    gap: 0.5rem;
    padding: 0.4rem 0;
    font-size: 0.8rem;
    color: var(--slate-500);
    border-bottom: 1px solid var(--slate-100);
}
.source-item:last-child { border-bottom: none; }
.source-num {
    flex: 0 0 1.5rem;
    font-weight: 600;
    color: var(--slate-400);
}
.source-link {
    color: var(--accent);
    text-decoration: none;
}
.source-link:hover { text-decoration: underline; }

/* ── Footer ── */
.footer {
    background: var(--slate-50);
    padding: 1rem 2rem;
    font-size: 0.75rem;
    color: var(--slate-400);
    text-align: center;
    border-top: 1px solid var(--slate-200);
}

/* ── Print ── */
@media print {
    body { background: white; padding: 0; }
    .report-container { box-shadow: none; }
    .hero { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


def _score_color(score: float) -> str:
    if score >= 75:
        return "score-high"
    elif score >= 50:
        return "score-med"
    return "score-low"


def _bar_color(score: float) -> str:
    if score >= 75:
        return "var(--accent)"
    elif score >= 50:
        return "var(--warning)"
    return "var(--danger)"


def _render_dimensions(ps: ProductScore) -> str:
    parts = []
    for d in ps.dimensions:
        label = DIM_LABELS.get(d.name, d.name)
        color = _bar_color(d.score)
        pct = max(2, int(d.score))
        parts.append(f"""
        <div class="dim-row">
            <span class="dim-label">{label}</span>
            <div class="dim-bar-bg">
                <div class="dim-bar-fill" style="width:{pct}%;background:{color};"></div>
            </div>
            <span class="dim-score">{d.score:.0f}</span>
        </div>""")
    return "\n".join(parts)


def _render_comparison_table(scored: list[ProductScore]) -> str:
    rows = []
    for ps in scored:
        is_best = ps.rank_in_batch == 1
        badge = '<span class="badge badge-best">★ Recommended</span>' if is_best else ''
        if ps.is_secondhand:
            badge += ' <span class="badge badge-secondhand">Refurb</span>'
        
        dim_map = {d.name: d.score for d in ps.dimensions}
        score_cls = _score_color(ps.total_weighted_score)
        price = ps.metadata.get("price", "?")
        shipping = ps.metadata.get("shipping_days", "?")
        
        rows.append(f"""
        <tr class="{'best' if is_best else ''}">
            <td>{ps.rank_in_batch}</td>
            <td><strong>{ps.product_name}</strong><br><small style="color:var(--slate-500)">{ps.vendor}</small>{badge}</td>
            <td class="price-cell">${price}</td>
            <td class="score-cell {score_cls}">{ps.total_weighted_score:.0f}</td>
            <td class="score-cell">{dim_map.get('quality', 0):.0f}</td>
            <td>{shipping}d</td>
        </tr>""")
    
    return f"""
    <table class="comp-table">
        <thead>
            <tr>
                <th>#</th>
                <th>Product / Vendor</th>
                <th>Price</th>
                <th>Score</th>
                <th>Quality</th>
                <th>Ship</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def generate_report(
    scored: list[ProductScore],
    product_query: str,
    search_timestamp: Optional[str] = None,
    savings_data: Optional[dict] = None,
) -> str:
    """
    Generate a complete HTML comparison report.
    
    Args:
        scored: List of scored products (sorted, ranked)
        product_query: The search query / product name
        search_timestamp: ISO timestamp of the search
        savings_data: Optional dict with annual_savings, fee, net_benefit
    
    Returns:
        Complete HTML document string
    """
    now = search_timestamp or datetime.now(timezone.utc).isoformat()
    best = scored[0] if scored else None
    
    # Savings hero
    savings_html = ""
    if savings_data:
        savings_html = f"""
        <div class="savings">${savings_data.get('annual_savings', '—')}</div>
        <div style="font-size:0.85rem;color:var(--slate-300);margin-top:0.25rem;">
            Estimated annual savings
        </div>"""
    
    # Recommendation
    rec_html = ""
    if best:
        rec_html = f"""
        <div class="recommendation">
            We recommend switching to <strong>{best.vendor}</strong> for <strong>{best.product_name}</strong>
        </div>"""
    
    # Confidence & risk
    confidence_pct = best.total_weighted_score if best else 0
    risk_label = "Low Risk" if confidence_pct >= 70 else "Medium Risk" if confidence_pct >= 50 else "High Risk"
    risk_color = "var(--accent)" if confidence_pct >= 70 else "var(--warning)" if confidence_pct >= 50 else "var(--danger)"
    
    # Comparison table
    comp_html = _render_comparison_table(scored)
    
    # Dimension breakdowns
    dim_htmls = []
    for ps in scored:
        dim_htmls.append(f"<h3 style='font-size:0.95rem;margin:1rem 0 0.5rem;'>{ps.product_name} — {ps.vendor} <span style='float:right;color:var(--accent);font-family:monospace;font-weight:700;'>{ps.total_weighted_score:.0f}/100</span></h3>")
        dim_htmls.append(_render_dimensions(ps))
        if ps.is_secondhand:
            dim_htmls.append('<small style="color:var(--warning);">⚠ Secondhand item — quality and warranty penalties applied</small>')
    dim_section = "\n".join(dim_htmls)
    
    # What-if scenarios
    scenario_html = _render_scenarios(scored)
    
    # Sources
    source_html = _render_sources(scored)
    
    # No strong alternative warning
    edge_case_html = ""
    if scored and scored[0].total_weighted_score < 65:
        edge_case_html = f"""
        <div class="section" style="background:rgba(220,38,38,0.05);border-left:4px solid var(--danger);">
            <h2><span class="icon">⚠️</span> No Strong Alternative Found</h2>
            <p style="font-size:0.9rem;color:var(--slate-600);">
                None of the available alternatives scored above 65/100. Consider:
            </p>
            <ul style="font-size:0.85rem;color:var(--slate-600);padding-left:1.2rem;margin-top:0.5rem;">
                <li><strong>Negotiate</strong> with your current vendor for better pricing</li>
                <li><strong>Wait</strong> for seasonal price drops (typically Q4)</li>
                <li><strong>Expand search</strong> to include refurbished or auction options</li>
            </ul>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sparrow Report — {product_query}</title>
<style>{CSS}</style>
</head>
<body>
<div class="report-container">

    <!-- HERO -->
    <div class="hero">
        <h1>💡 Savings Opportunity Identified</h1>
        {rec_html}
        {savings_html}
        <div class="meta">
            <span><strong>Confidence:</strong> {confidence_pct:.0f}%</span>
            <span><strong>Risk:</strong> <span style="color:{risk_color}">{risk_label}</span></span>
            <span><strong>Search:</strong> {now[:19]}</span>
            <span><strong>Options:</strong> {len(scored)}</span>
        </div>
    </div>

    <!-- COMPARISON TABLE -->
    <div class="section">
        <h2><span class="icon">📊</span> Comparison Overview</h2>
        {comp_html}
    </div>

    <!-- DIMENSION BREAKDOWN -->
    <div class="section">
        <h2><span class="icon">🔍</span> Dimension Breakdown</h2>
        {dim_section}
    </div>

    <!-- WHAT-IF SCENARIOS -->
    <div class="section">
        <h2><span class="icon">🎯</span> What-If Scenarios</h2>
        {scenario_html}
    </div>

    <!-- EDGE CASE -->
    {edge_case_html}

    <!-- SOURCES -->
    <div class="section">
        <h2><span class="icon">📎</span> Sources & Provenance</h2>
        {source_html}
    </div>

    <!-- FOOTER -->
    <div class="footer">
        Generated by Sparrow AI · Product Comparison Report · {now[:19]} UTC<br>
        Scores based on 8-dimension rubric · Data refreshed at time of search
    </div>

</div>
</body>
</html>"""
    return html


def _render_scenarios(scored: list[ProductScore]) -> str:
    """Render priority-based scenario cards."""
    if not scored:
        return "<p>No data available.</p>"

    # Price winner
    def price_key(ps):
        p = ps.metadata.get("price")
        if isinstance(p, (int, float)):
            return p
        return float("inf")
    price_winner = min(scored, key=price_key)
    
    # Quality winner
    quality_winner = max(scored, key=lambda s: next((d.score for d in s.dimensions if d.name == "quality"), 0))
    
    # Fastest ship
    def ship_key(ps):
        d = ps.metadata.get("shipping_days")
        if isinstance(d, (int, float)):
            return d
        return 999
    fastest_winner = min(scored, key=ship_key)

    cards = []
    scenarios = [
        ("Prioritize Price", price_winner, "Lowest total landed cost"),
        ("Prioritize Quality", quality_winner, "Highest quality/reliability score"),
        ("Need It Fastest", fastest_winner, f"Estimated {fastest_winner.metadata.get('shipping_days', '?')} day delivery"),
    ]
    
    for title, winner, why in scenarios:
        cards.append(f"""
        <div class="scenario-card">
            <h3>{title}</h3>
            <div class="pick">{winner.product_name} — {winner.vendor}</div>
            <div class="why">{why} (Score: {winner.total_weighted_score:.0f})</div>
        </div>""")

    return "<div class='scenarios'>" + "".join(cards) + "</div>"


def _render_sources(scored: list[ProductScore]) -> str:
    """Render source citations from product metadata."""
    parts = []
    for i, ps in enumerate(scored, 1):
        source_line = f'<a href="{ps.url}" class="source-link" target="_blank">{ps.url}</a>' if ps.url else "Internal data"
        parts.append(f"""
        <div class="source-item">
            <span class="source-num">{i}.</span>
            <span><strong>{ps.vendor}</strong> — {source_line}</span>
        </div>""")
    
    if not parts:
        return "<p>No sources available.</p>"
    
    return "\n".join(parts)
