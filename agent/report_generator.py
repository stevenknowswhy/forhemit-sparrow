from __future__ import annotations
import json
import io
from datetime import datetime, timezone
from typing import Optional

from scorer import (
    ProductScore, format_dimension_breakdown,
    DIM_LABELS, DIMENSIONS,
    get_preset_labels, get_preset, RUBRIC_PRESETS,
)


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
    padding: 0;
}

.sticky-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--navy);
    color: var(--white);
    padding: 0.6rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.85rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.sticky-nav .nav-brand {
    font-weight: 700;
    font-size: 0.9rem;
}
.sticky-nav .nav-brand span {
    color: var(--accent-light);
}
.sticky-nav .nav-meta {
    display: flex;
    gap: 1.5rem;
    color: var(--slate-300);
}
.sticky-nav .nav-meta strong {
    color: var(--white);
}

.report-container {
    max-width: 860px;
    margin: 0 auto;
    background: var(--white);
    border-radius: 0 0 var(--radius) var(--radius);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}

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

.hero-actions {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-top: 1.5rem;
    flex-wrap: wrap;
}
.btn-invoke {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1.5rem;
    background: var(--accent);
    color: var(--white);
    border: none;
    border-radius: var(--radius);
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.2s;
    text-decoration: none;
}
.btn-invoke:hover {
    background: #047857;
}
.btn-reject {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem 1.5rem;
    background: transparent;
    color: var(--slate-300);
    border: 1px solid var(--slate-500);
    border-radius: var(--radius);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
}
.btn-reject:hover {
    border-color: var(--danger);
    color: var(--danger);
}

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

.dim-row {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.5rem 0;
    font-size: 0.85rem;
}
.dim-top {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
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
.dim-rationale {
    margin: 0.15rem 0 0 180px;
    font-size: 0.78rem;
    color: var(--slate-500);
    font-style: italic;
    padding-left: 0.75rem;
    border-left: 2px solid var(--slate-200);
}

.scenarios {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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

.fee-display {
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}
.fee-item {
    text-align: center;
    min-width: 100px;
}
.fee-item .label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--slate-400);
}
.fee-item .value {
    font-size: 1.3rem;
    font-weight: 700;
    font-family: 'SF Mono', 'Fira Code', monospace;
}
.fee-item .value.positive { color: var(--accent-light); }
.fee-item .value.negative { color: var(--danger); }
.fee-item .value.neutral { color: var(--white); }

.traffic-light {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
}
.traffic-light .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}
.traffic-light .dot.green { background: var(--accent); }
.traffic-light .dot.amber { background: var(--warning); }
.traffic-light .dot.red { background: var(--danger); }

.savings-positive { color: var(--accent); font-weight: 600; }
.savings-neutral { color: var(--slate-400); }

.secondhand-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.secondhand-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1rem;
    background: var(--slate-50);
    border: 1px solid var(--slate-200);
    border-radius: var(--radius);
}
.secondhand-item .condition-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    white-space: nowrap;
}
.badge-refurb { background: #fef3c7; color: #92400e; }
.badge-openbox { background: #dbeafe; color: #1e40af; }
.badge-auction { background: #fee2e2; color: #991b1b; }
.badge-new { background: #d1fae5; color: #065f46; }

.risk-warning {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-radius: var(--radius);
    background: rgba(220,38,38,0.05);
    border-left: 4px solid var(--danger);
    margin-top: 0.5rem;
    font-size: 0.85rem;
    color: var(--slate-600);
}

.collapsible-header {
    cursor: pointer;
    user-select: none;
}
.collapsible-header::before {
    content: "\u25be ";
    font-size: 0.8rem;
    transition: transform 0.2s;
}
.collapsible-header.collapsed::before {
    content: "\u25b8 ";
}
.collapsible-body {
    overflow: hidden;
    transition: max-height 0.3s ease;
}
.collapsible-body.collapsed {
    max-height: 0 !important;
}

.toggle-bar {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}
.toggle-btn {
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    border: 1px solid var(--slate-300);
    border-radius: 20px;
    background: var(--white);
    color: var(--slate-600);
    cursor: pointer;
    transition: all 0.2s;
}
.toggle-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
}
.toggle-btn.active {
    background: var(--accent);
    color: var(--white);
    border-color: var(--accent);
}

.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.4);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}
.modal-overlay.open {
    display: flex;
}
.modal-content {
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    max-width: 540px;
    width: 90%;
    padding: 1.5rem;
}
.modal-content h3 {
    margin-bottom: 0.5rem;
}
.modal-content textarea {
    width: 100%;
    min-height: 140px;
    border: 1px solid var(--slate-300);
    border-radius: var(--radius);
    padding: 0.75rem;
    font-family: system-ui, sans-serif;
    font-size: 0.85rem;
    resize: vertical;
    margin: 0.75rem 0;
}
.modal-close {
    background: var(--slate-100);
    border: none;
    border-radius: var(--radius);
    padding: 0.4rem 1rem;
    cursor: pointer;
    font-size: 0.85rem;
}
.modal-close:hover {
    background: var(--slate-200);
}

.footer {
    background: var(--slate-50);
    padding: 1rem 2rem;
    font-size: 0.75rem;
    color: var(--slate-400);
    text-align: center;
    border-top: 1px solid var(--slate-200);
}

@media print {
    body { background: white; padding: 0; }
    .report-container { box-shadow: none; }
    .sticky-nav { position: static; }
    .toggle-bar, .collapsible-header::before, .modal-overlay, .hero-actions { display: none; }
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


def _score_to_color_hex(score: float) -> str:
    if score >= 75:
        return "#059669"
    elif score >= 50:
        return "#d97706"
    return "#dc2626"


def _render_dimensions(ps: ProductScore, labels: dict[str, str], dim_averages: Optional[dict[str, float]] = None) -> str:
    parts = []
    for d in ps.dimensions:
        if d.weight == 0:
            continue
        label = labels.get(d.name, d.name)
        color = _bar_color(d.score)
        pct = max(2, int(d.score))
        has_data = ps.data_quality.get(d.name, False)
        dot = '<span style="color:var(--accent);font-size:1.1rem;">\u25cf</span>' if has_data else '<span style="color:var(--slate-300);font-size:1.1rem;">\u25cb</span>'

        insight = ""
        if dim_averages and d.name in dim_averages:
            avg = dim_averages[d.name]
            if d.score >= avg + 10:
                insight = '<span style="font-size:0.75rem;color:var(--accent);margin-left:0.5rem;">\u2191 Above avg</span>'
            elif d.score <= avg - 10:
                insight = '<span style="font-size:0.75rem;color:var(--danger);margin-left:0.5rem;">\u2193 Below avg</span>'
            else:
                insight = '<span style="font-size:0.75rem;color:var(--slate-400);margin-left:0.5rem;">\u2014 At avg</span>'

        rationale_html = ""
        if d.rationale:
            rationale_html = f'<div class="dim-rationale">{d.rationale}</div>'

        parts.append(f"""
        <div class="dim-row">
            <div style="width:100%;">
                <div class="dim-top">
                    <span class="dim-label">{dot} {label}{insight}</span>
                    <div class="dim-bar-bg">
                        <div class="dim-bar-fill" style="width:{pct}%;background:{color};"></div>
                    </div>
                    <span class="dim-score">{d.score:.0f}</span>
                </div>
                {rationale_html}
            </div>
        </div>""")
    return "\n".join(parts)


def _render_comparison_table(scored: list[ProductScore]) -> str:
    prices = [
        ps.metadata.get("price", 0) for ps in scored
        if isinstance(ps.metadata.get("price"), (int, float))
    ]
    baseline = max(prices) if prices else 0
    rows = []
    for ps in scored:
        is_best = ps.rank_in_batch == 1
        badge = '<span class="badge badge-best">\u2605 Recommended</span>' if is_best else ''
        if ps.is_secondhand:
            badge += ' <span class="badge badge-secondhand">Refurb</span>'

        dim_map = {d.name: d.score for d in ps.dimensions}
        score_cls = _score_color(ps.total_weighted_score)
        price = ps.metadata.get("price", "?")
        shipping = ps.metadata.get("shipping_days", "?")

        if isinstance(price, (int, float)) and baseline:
            annual_savings = (baseline - price) * 4
            savings_cell = f'<span class="savings-positive">${annual_savings:.0f}</span>' if annual_savings > 0 else '<span class="savings-neutral">\u2014</span>'
        else:
            savings_cell = '<span class="savings-neutral">\u2014</span>'

        sh_attr = ' data-secondhand="true"' if ps.is_secondhand else ''
        rows.append(f"""
        <tr class="{'best' if is_best else ''}"{sh_attr}>
            <td>{ps.rank_in_batch}</td>
            <td><strong>{ps.product_name}</strong><br><small style="color:var(--slate-500)">{ps.vendor}</small>{badge}</td>
            <td class="price-cell">${price}</td>
            <td class="score-cell {score_cls}" title="Score: {ps.total_weighted_score:.0f}/100">{ps.total_weighted_score:.0f}</td>
            <td class="score-cell" title="Quality score">{dim_map.get('quality', 0):.0f}</td>
            <td title="Shipping: {shipping}d">{shipping}d</td>
            <td class="price-cell">{savings_cell}</td>
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
                <th>Annual Savings</th>
            </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def _render_sticky_header(scored: list[ProductScore], preset_label: str, now: str) -> str:
    best = scored[0] if scored else None
    if not best:
        return ""
    confidence_pct = best.confidence * 100
    return f"""
    <div class="sticky-nav">
        <div class="nav-brand">Sparrow <span>CFO</span></div>
        <div class="nav-meta">
            <span><strong>{best.product_name}</strong> \u2014 {best.vendor}</span>
            <span>Score: <strong>{best.total_weighted_score:.0f}</strong></span>
            <span>Confidence: <strong>{confidence_pct:.0f}%</strong></span>
            <span>{preset_label} Rubric</span>
        </div>
    </div>"""


def _render_actions() -> str:
    return """
    <div class="hero-actions">
        <button class="btn-invoke" data-action="invoke">\u2713 Invoke \u2014 Switch to Recommended</button>
        <button class="btn-reject" data-action="reject">\u2717 Reject \u2014 Stay with Current</button>
    </div>"""


def generate_report(
    scored: list[ProductScore],
    product_query: str,
    search_timestamp: Optional[str] = None,
    savings_data: Optional[dict] = None,
    preset: str = "consumer",
    validation: Optional[dict] = None,
    ai_validation: Optional[dict] = None,
) -> str:
    now = search_timestamp or datetime.now(timezone.utc).isoformat()
    preset_def = get_preset(preset)
    preset_label = preset_def["label"]
    labels = get_preset_labels(preset)

    best = scored[0] if scored else None

    # ── Hero ──────────────────────────────────────────────────
    savings_html = ""
    fee_html = ""
    if savings_data:
        annual = savings_data.get('annual_savings', '\u2014')
        fee = savings_data.get('fee', '\u2014')
        net = savings_data.get('net_benefit', '\u2014')
        savings_html = f"""
        <div class="savings">${annual}</div>
        <div style="font-size:0.85rem;color:var(--slate-300);margin-top:0.25rem;">
            Estimated annual savings
        </div>"""
        fee_html = f"""
        <div class="fee-display">
            <div class="fee-item">
                <div class="label">Baseline Spend</div>
                <div class="value neutral">${savings_data.get('baseline', annual)}</div>
            </div>
            <div class="fee-item">
                <div class="label">Sparrow Fee</div>
                <div class="value negative">${fee}</div>
            </div>
            <div class="fee-item">
                <div class="label">Net Benefit</div>
                <div class="value positive">${net}</div>
            </div>
        </div>"""

    rec_html = ""
    if best:
        rec_html = f"""
        <div class="recommendation">
            We recommend switching to <strong>{best.vendor}</strong> for <strong>{best.product_name}</strong>
        </div>"""

    confidence_pct = (best.confidence * 100) if best else 0
    if confidence_pct >= 70:
        risk_label = "Low Risk"
        risk_dot = "green"
    elif confidence_pct >= 50:
        risk_label = "Medium Risk"
        risk_dot = "amber"
    else:
        risk_label = "High Risk"
        risk_dot = "red"

    # ── Section 2: Comparison Table ──────────────────────────
    comp_html = _render_comparison_table(scored)

    # ── Section 3: Dimension Breakdown ────────────────────────
    dim_averages: dict[str, float] = {}
    if scored:
        for idx, d in enumerate(scored[0].dimensions):
            vals = [
                ps.dimensions[idx].score for ps in scored
                if idx < len(ps.dimensions) and ps.dimensions[idx].score is not None
            ]
            if vals:
                dim_averages[d.name] = sum(vals) / len(vals)

    dim_htmls = []
    for i, ps in enumerate(scored):
        secondhand_attr = ' data-secondhand="true"' if ps.is_secondhand else ''
        dim_htmls.append(
            f'<div class="product-dims" data-product-index="{i}"{secondhand_attr}>'
            f'<h3 class="collapsible-header" data-action="toggle-collapse" '
            f'title="Click to expand/collapse dimensions">'
            f'{ps.product_name} \u2014 {ps.vendor} '
            f'<span style="float:right;color:var(--accent);font-family:monospace;font-weight:700;">'
            f'{ps.total_weighted_score:.0f}/100</span></h3>'
        )
        dim_htmls.append('<div class="collapsible-body">')
        dim_htmls.append(_render_dimensions(ps, labels, dim_averages))
        dq_count = sum(1 for v in ps.data_quality.values() if v)
        dim_htmls.append(
            f'<div style="font-size:0.75rem;color:var(--slate-400);text-align:right;">'
            f'\u25cf = data-backed \u00a0\u25cb = default \u00a0|\u00a0 '
            f'<strong>{dq_count}/{len(ps.dimensions)}</strong> dimensions with data'
            f'</div>'
        )
        if ps.url:
            dim_htmls.append(
                f'<div style="font-size:0.75rem;color:var(--slate-400);text-align:right;">'
                f'Source: <a href="{ps.url}" style="color:var(--accent);text-decoration:none;" target="_blank">{ps.url}</a>'
                f'</div>'
            )
        if ps.is_secondhand:
            dim_htmls.append(
                '<small style="color:var(--warning);">'
                '\u26a0 Secondhand item \u2014 quality and warranty penalties applied</small>'
            )
        dim_htmls.append('</div></div>')
    dim_section = "\n".join(dim_htmls)

    # ── Section 4: What-If Scenarios ─────────────────────────
    scenario_html = _render_scenarios(scored)
    validation_html = _render_validation_section(validation)
    ai_judge_html = _render_ai_judge_section(ai_validation)
    # ── Section 5: Secondhand ────────────────────────────────
    secondhand_html = _render_secondhand_section(scored)
    # ── Section 6: Sources ───────────────────────────────────
    source_html = _render_sources(scored)
    # ── Section 7: Edge Case ─────────────────────────────────
    edge_case_html = _render_edge_case(scored, product_query)

    # Sticky nav
    sticky_html = _render_sticky_header(scored, preset_label, now)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sparrow CFO Pro Buyer \u2014 {product_query}</title>
<style>{CSS}</style>
</head>
<body>
{sticky_html}
<div class="report-container">

    {_render_hero(product_query, rec_html, savings_html, fee_html, confidence_pct, risk_dot, risk_label, now, scored)}

    {_render_actions()}

    <div class="section">
        <h2><span class="icon">\U0001f4ca</span> \u00a72 \u2014 Comparison Table</h2>
        <div class="toggle-bar">
            <button class="toggle-btn active" data-action="toggle-new-only" id="new-only-btn">\U0001f331 New Items Only</button>
            <button class="toggle-btn" data-action="expand-all-dims" id="expand-all-btn">\u25bc Expand All Dimensions</button>
        </div>
        {comp_html}
    </div>

    <div class="section">
        <h2><span class="icon">\U0001f50d</span> \u00a73 \u2014 Dimension Breakdown <span style="font-size:0.7rem;color:var(--slate-400);font-weight:400;">({preset_label} rubric)</span></h2>
        <p style="font-size:0.85rem;color:var(--slate-500);margin-bottom:0.75rem;">Each dimension scored 0\u2013100. \u25cf = data-backed, \u25cb = default value. Hover or expand for details.</p>
        {dim_section}
    </div>

    <div class="section">
        <h2><span class="icon">\U0001f3af</span> \u00a74 \u2014 What-If Scenarios</h2>
        <p style="font-size:0.85rem;color:var(--slate-500);margin-bottom:0.75rem;">How different priorities change the recommendation.</p>
        {scenario_html}
    </div>

    {validation_html}

    {ai_judge_html}

    {secondhand_html}

    {edge_case_html}

    <div class="section">
        <h2><span class="icon">\U0001f4ce</span> \u00a76 \u2014 Sources &amp; Provenance</h2>
        <p style="font-size:0.85rem;color:var(--slate-500);margin-bottom:0.75rem;">Timestamps, confidence levels, and provenance for each data point.</p>
        {source_html}
    </div>

    <div class="footer">
        Generated by Sparrow AI \u00b7 {preset_label} Rubric \u00b7 CFO Pro Buyer Report \u00b7 {now[:19]} UTC<br>
        Scores based on 8-dimension rubric \u00b7 Data refreshed at time of search
    </div>

</div>

<script>
document.addEventListener('click', function(e) {{
    var el = e.target;
    var action = el.getAttribute('data-action');
    if (!action) return;

    function findParent(el, tag) {{
        tag = tag.toUpperCase();
        while (el && el.tagName !== tag) el = el.parentElement;
        return el;
    }}

    var fn = {{
        'toggle-collapse': function() {{
            el.classList.toggle('collapsed');
            var body = el.nextElementSibling;
            if (!body) return;
            body.classList.toggle('collapsed');
            if (body.style.maxHeight) body.style.maxHeight = null;
            else body.style.maxHeight = body.scrollHeight + 'px';
        }},
        'toggle-new-only': function() {{
            var btn = el;
            var showingNew = btn.classList.toggle('active');
            btn.textContent = showingNew ? '\U0001f331 New Items Only' : '\U0001f4e6 Show All Items';
            var sel = '[data-secondhand="true"]';
            document.querySelectorAll('.comp-table ' + sel + ', .product-dims' + sel).forEach(function(el) {{
                el.style.display = showingNew ? 'none' : '';
            }});
            document.querySelectorAll('.secondhand-item').forEach(function(el) {{
                el.closest('.section').style.display = showingNew ? 'none' : '';
            }});
        }},
        'expand-all-dims': function() {{
            document.querySelectorAll('.collapsible-body.collapsed').forEach(function(body) {{
                body.classList.remove('collapsed');
                body.style.maxHeight = body.scrollHeight + 'px';
                var hdr = body.previousElementSibling;
                if (hdr) hdr.classList.remove('collapsed');
            }});
        }},
        'open-negotiate': function() {{
            document.getElementById('negotiate-modal').classList.add('open');
        }},
        'close-negotiate': function() {{
            document.getElementById('negotiate-modal').classList.remove('open');
        }},
        'copy-email': function() {{
            var ta = document.getElementById('negotiate-email');
            ta.select();
            navigator.clipboard.writeText(ta.value);
            var orig = el.textContent;
            el.textContent = '\u2705 Copied!';
            setTimeout(function() {{ el.textContent = orig; }}, 2000);
        }},
        'invoke': function() {{
            alert('Invoke action triggered. In a production Tauri app this would open the order workflow.');
        }},
        'reject': function() {{
            alert('Reject action triggered. In a production Tauri app this would log feedback.');
        }},
    }}[action];
    if (fn) fn();
}});

document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('.collapsible-body').forEach(function(body) {{
        body.style.maxHeight = body.scrollHeight + 'px';
    }});
}});

document.getElementById('negotiate-modal').addEventListener('click', function(e) {{
    if (e.target === this) this.classList.remove('open');
}});
</script>
</body>
</html>"""
    return html


def _render_hero(product_query: str, rec_html: str, savings_html: str, fee_html: str,
                 confidence_pct: float, risk_dot: str, risk_label: str,
                 now: str, scored: list[ProductScore]) -> str:
    return f"""
    <div class="hero">
        <h1>\U0001f4a1 Savings Opportunity Identified</h1>
        {rec_html}
        {savings_html}
        {fee_html}
        <div class="meta">
            <span><strong>Confidence:</strong> {confidence_pct:.0f}%</span>
            <span><strong>Risk:</strong> <span class="traffic-light"><span class="dot {risk_dot}"></span>{risk_label}</span></span>
            <span><strong>Search:</strong> {now[:19]}</span>
            <span><strong>Options:</strong> {len(scored)}</span>
        </div>
    </div>"""


def _render_scenarios(scored: list[ProductScore]) -> str:
    if not scored:
        return "<p>No data available.</p>"

    def price_key(ps):
        p = ps.metadata.get("price")
        if isinstance(p, (int, float)):
            return p
        return float("inf")
    price_winner = min(scored, key=price_key)

    quality_winner = max(scored, key=lambda s: next((d.score for d in s.dimensions if d.name == "quality"), 0))

    def ship_key(ps):
        d = ps.metadata.get("shipping_days")
        if isinstance(d, (int, float)):
            return d
        return 999
    fastest_winner = min(scored, key=ship_key)

    def score_to_price_ratio(ps):
        p = ps.metadata.get("price")
        if isinstance(p, (int, float)) and p > 0:
            return ps.total_weighted_score / p
        return 0
    balance_winner = max(scored, key=score_to_price_ratio)

    def bulk_price_key(ps):
        p = ps.metadata.get("price")
        if isinstance(p, (int, float)):
            free_shipping = ps.metadata.get("free_shipping", False)
            bulk_p = p * 0.9
            if free_shipping:
                return bulk_p
            return bulk_p + (ps.metadata.get("shipping_cost") or 5.0)
        return float("inf")
    bulk_winner = min(scored, key=bulk_price_key)

    cards = []
    scenarios = [
        ("\U0001f4b0 Prioritize Price", price_winner, "Lowest total landed cost"),
        ("\u2b50 Prioritize Quality", quality_winner, "Highest quality/reliability score"),
        ("\U0001f698 Need It Fastest", fastest_winner, f"Estimated {fastest_winner.metadata.get('shipping_days', '?')} day delivery"),
        ("\u2696\ufe0f Best Balance", balance_winner, "Best score-to-price ratio"),
        ("\U0001f4e6 Buy in Bulk", bulk_winner,
         f"10% volume discount + logistics — estimated {bulk_winner.metadata.get('price', '?')} per unit"),
    ]

    for title, winner, why in scenarios:
        cards.append(f"""
        <div class="scenario-card">
            <h3>{title}</h3>
            <div class="pick">{winner.product_name} \u2014 {winner.vendor}</div>
            <div class="why">{why} (Score: {winner.total_weighted_score:.0f})</div>
        </div>""")

    return "<div class='scenarios'>" + "".join(cards) + "</div>"


def _render_validation_section(
    validation: Optional[dict] = None,
) -> str:
    if not validation:
        return ""
    global_vr = validation.get("__global__")
    per_product_flags = [
        vr for key, vr in validation.items()
        if key != "__global__" and vr.flags
    ]
    all_flags = list(global_vr.flags) if global_vr else []
    for vr in per_product_flags:
        all_flags.extend(vr.flags)
    if not all_flags:
        return ""

    rows = []
    for f in all_flags:
        icon = {"info": "\u2139\ufe0f", "warning": "\u26a0\ufe0f", "error": "\U0001f6ab"}.get(f.severity, "\u2022")
        color = {"info": "var(--slate-400)", "warning": "var(--warning)", "error": "var(--danger)"}.get(f.severity, "var(--slate-400)")
        rows.append(f"""
        <div style="display:flex;gap:0.5rem;padding:0.4rem 0;border-bottom:1px solid var(--slate-100);font-size:0.85rem;">
            <span>{icon}</span>
            <div style="flex:1;">
                <strong style="color:{color};">{f.field}</strong>
                <span style="color:var(--slate-600);margin-left:0.3rem;">{f.message}</span>
                <div style="font-size:0.8rem;color:var(--slate-400);margin-top:0.15rem;">
                    {f.product_vendor} \u2014 {f.suggestion}
                </div>
            </div>
        </div>""")

    return f"""
    <div class="section" style="background:rgba(245,158,11,0.03);border-left:4px solid var(--warning);">
        <h2><span class="icon">\U0001f6e1\ufe0f</span> Validation &amp; Cross-Check</h2>
        <div style="margin-top:0.5rem;">{"".join(rows)}</div>
    </div>"""


def _render_ai_judge_section(
    ai_validation: Optional[dict] = None,
) -> str:
    if not ai_validation:
        return ""
    global_vr = ai_validation.get("__global__")
    per_product = [
        vr for key, vr in ai_validation.items()
        if key != "__global__" and vr.flags
    ]
    all_flags = list(global_vr.flags) if global_vr else []
    for vr in per_product:
        all_flags.extend(vr.flags)
    if not all_flags:
        return ""

    rows = []
    for f in all_flags:
        severity_color = {"info": "var(--slate-400)", "warning": "var(--warning)", "error": "var(--danger)"}.get(f.severity, "var(--slate-400)")
        severity_tag = {"info": "info", "warning": "warning", "error": "error"}.get(f.severity, "info")
        rows.append(f"""
        <div style="display:flex;gap:0.5rem;padding:0.5rem 0;border-bottom:1px solid var(--slate-100);font-size:0.85rem;">
            <div style="flex:0 0 2rem;text-align:center;">
                <span style="font-size:0.7rem;background:var(--navy);color:var(--white);padding:0.15rem 0.4rem;border-radius:4px;">AI</span>
            </div>
            <div style="flex:1;">
                <div>
                    <span style="font-size:0.7rem;background:rgba(245,158,11,0.1);color:{severity_color};padding:0.1rem 0.35rem;border-radius:3px;margin-right:0.3rem;text-transform:uppercase;">{severity_tag}</span>
                    <strong style="color:{severity_color};">{f.field}</strong>
                    <span style="color:var(--slate-600);margin-left:0.3rem;">{f.message}</span>
                </div>
                <div style="font-size:0.8rem;color:var(--slate-400);margin-top:0.15rem;">
                    {f.product_vendor} \u2014 {f.suggestion}
                </div>
            </div>
        </div>""")

    return f"""
    <div class="section" style="background:rgba(15,23,42,0.03);border-left:4px solid var(--navy);">
        <h2><span class="icon">\U0001f916</span> AI Judge Analysis</h2>
        <p style="font-size:0.8rem;color:var(--slate-400);margin-bottom:0.5rem;">
            LLM-powered cross-check of product scores against raw source text.
            These flags are probabilistic \u2014 verify before acting.
        </p>
        <div style="margin-top:0.5rem;">{"".join(rows)}</div>
    </div>"""


def _render_secondhand_section(scored: list[ProductScore]) -> str:
    sh_items = [ps for ps in scored if ps.is_secondhand]
    if not sh_items:
        return ""

    items_html = []
    for ps in sh_items:
        grade = ps.metadata.get("secondhand_grade", "used")
        if grade in ("certified_refurbished", "refurbished"):
            badge_cls = "badge-refurb"
            badge_label = "Refurbished"
        elif grade in ("open_box", "like_new"):
            badge_cls = "badge-openbox"
            badge_label = "Open-Box"
        elif grade == "auction":
            badge_cls = "badge-auction"
            badge_label = "Auction"
        else:
            badge_cls = "badge-refurb"
            badge_label = grade.replace("_", " ").title()

        quality_penalty = ps.metadata.get("quality_penalty", 0)
        penalty_str = f"Quality Penalty: -{quality_penalty:.0f}% applied"

        items_html.append(f"""
        <div class="secondhand-item">
            <span class="condition-badge {badge_cls}">{badge_label}</span>
            <div style="flex:1;">
                <strong>{ps.product_name}</strong>
                <span style="color:var(--slate-500);font-size:0.85rem;"> \u2014 {ps.vendor}</span>
                <div style="font-size:0.8rem;color:var(--slate-400);margin-top:0.15rem;">
                    Score: {ps.total_weighted_score:.0f}/100 \u00b7 {penalty_str}
                </div>
            </div>
        </div>""")

    risk_warning = ""
    if any(ps.metadata.get("secondhand_grade") == "auction" for ps in sh_items):
        risk_warning = """
        <div class="risk-warning">
            <span style="font-size:1.1rem;">\u26a0\ufe0f</span>
            <div>
                <strong>Auction items</strong> \u2014 final price not guaranteed. Price shown is estimated.
                Verify seller rating and return policy before purchasing.
            </div>
        </div>"""

    return f"""
    <div class="section">
        <h2><span class="icon">\U0001f504</span> \u00a75 \u2014 Secondhand &amp; Auction Options</h2>
        <div class="secondhand-list">{"".join(items_html)}</div>
        {risk_warning}
    </div>"""


def _render_sources(scored: list[ProductScore]) -> str:
    parts = []
    for i, ps in enumerate(scored, 1):
        source_line = f'<a href="{ps.url}" class="source-link" target="_blank">{ps.url}</a>' if ps.url else "Internal data"
        confidence_pct = ps.confidence * 100
        dq_count = sum(1 for v in ps.data_quality.values() if v)
        total_dims = len(ps.dimensions)
        parts.append(f"""
        <div class="source-item">
            <span class="source-num">{i}.</span>
            <div style="flex:1;">
                <div><strong>{ps.vendor}</strong> \u2014 {source_line}</div>
                <div style="font-size:0.75rem;color:var(--slate-400);margin-top:0.15rem;">
                    Confidence: {confidence_pct:.0f}% \u00b7 Data coverage: {dq_count}/{total_dims} dimensions
                </div>
            </div>
        </div>""")

    if not parts:
        return "<p>No sources available.</p>"

    return "\n".join(parts)


def _render_edge_case(scored: list[ProductScore], product_query: str) -> str:
    if not scored or scored[0].total_weighted_score >= 65:
        return ""
    best_vendor = scored[0].vendor
    return f"""
    <div class="section" style="background:rgba(220,38,38,0.05);border-left:4px solid var(--danger);">
        <h2><span class="icon">\u26a0\ufe0f</span> \u00a77 \u2014 No Strong Alternative Found</h2>
        <p style="font-size:0.9rem;color:var(--slate-600);">
            None of the available alternatives scored above 65/100. Consider:
        </p>
        <ul style="font-size:0.85rem;color:var(--slate-600);padding-left:1.2rem;margin-top:0.5rem;">
            <li><strong>Negotiate</strong> with your current vendor for better pricing
                <button class="toggle-btn" data-action="open-negotiate" style="margin-left:0.5rem;font-size:0.75rem;">\u2709\ufe0f Draft Email</button>
            </li>
            <li><strong>Wait</strong> for seasonal price drops (typically Q4)</li>
            <li><strong>Expand search</strong> to include refurbished or auction options</li>
        </ul>
    </div>
    <div class="modal-overlay" id="negotiate-modal">
        <div class="modal-content">
            <h3>\U0001f4dd Negotiation Email Draft</h3>
            <p style="font-size:0.85rem;color:var(--slate-500);margin-bottom:0.5rem;">
                Copy this email and send to your current vendor:
            </p>
            <textarea id="negotiate-email" readonly>Subject: Pricing Discussion \u2014 {product_query}

Dear {best_vendor} Sales Team,

We are currently evaluating our office supply procurement for {product_query}
and have identified potential savings by switching vendors.

We value our relationship with {best_vendor} and would prefer to continue
our partnership, but we need pricing that is competitive with alternatives
currently available in the market.

Could you please provide your best pricing on {product_query} for a
volume commitment? We are looking for:

\u2022 Competitive unit pricing
\u2022 Volume discount tiers
\u2022 Free shipping options
\u2022 Extended warranty terms

We look forward to your response.

Best regards,
[Your Name]</textarea>
            <button class="modal-close" data-action="copy-email">\U0001f4cb Copy to Clipboard</button>
            <button class="modal-close" data-action="close-negotiate" style="float:right;">Close</button>
        </div>
    </div>"""
