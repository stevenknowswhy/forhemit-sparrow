# Sparrow CFO Pro Buyer — Report Template Design

## Goal
Create a beautiful, reusable HTML/CSS report template that the CFO Pro Buyer Agent always produces when researching a product. The user should be able to quickly scan, understand, and make a decision.

## Design Principles
- **Scan in 10 seconds** — headline savings at top, color-coded scores, clear recommendation
- **Trust through transparency** — sources cited, confidence shown, "show your work"
- **Action-oriented** — prominent Invoke/Reject buttons, fee clearly shown
- **Mobile-friendly** — readable on desktop and tablet
- **No frameworks** — pure HTML/CSS, no JavaScript dependencies (unless needed for interactivity)

## Report Sections (in order)

### 1. HERO — Executive Summary
- Big headline: "We recommend switching to [Vendor] for [Product]"
- Key metric: Annual savings amount (big, bold)
- Fee: Sparrow cut (small, transparent)
- Net benefit: After fee
- Confidence meter
- Risk indicator (traffic light)

### 2. COMPARISON TABLE
- Side-by-side: Current vs. Top 3 alternatives
- Score column with color coding
- Quick specs row
- Annual savings per option

### 3. WHY THIS WINNERS — Dimension Breakdown
- Expandable rows for each of the 8 dimensions
- Score bar for each
- Key insight per dimension
- Source citation

### 4. WHAT-IF SCENARIOS
- If you prioritize price → [Option A]
- If you prioritize quality → [Option B]
- If you buy in bulk → [Option C]

### 5. SECONDHAND/AUCTION (if toggle ON)
- Separate section with condition badges
- Risk warnings if applicable
- Quality penalty clearly shown

### 6. SOURCES & PROVENANCE
- Where each data point came from
- Timestamp
- Confidence level

### 7. EDGE CASE — No Strong Alternative
- If no option scores ≥ 65
- "Negotiate Instead" option
- "Wait for Price Drop" suggestion

## Visual Design System

### Colors
- Primary: Deep navy (#0f172a) — professional, trustworthy
- Accent: Emerald green (#059669) — savings, positive action
- Warning: Amber (#d97706) — trade-offs, medium risk
- Danger: Red (#dc2626) — high risk, reject
- Neutral: Slate grays (#64748b, #94a3b8, #cbd5e1)
- Background: White/light gray
- Score bars: Gradient from red → amber → green

### Typography
- Headings: System font stack (SF Pro / Inter-like)
- Numbers: Monospace for prices, scores
- Body: Clean sans-serif
- Large headline numbers (savings, score)

### Layout
- Max-width: 800px for readability
- Card-based sections with subtle shadows
- Sticky header with product name
- Print-friendly

### Interactive Elements (optional JS)
- Expand/collapse dimension breakdown
- Toggle between "New Only" vs "Include Refurbished" view
- Hover tooltips on scores
- "Negotiate Instead" email draft modal
