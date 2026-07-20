# Sparrow Report Template — Astryx Design System

## Components Used from Astryx

### Layout
- `HStack` / `VStack` — Vertical stacking for sections, horizontal for stat cards
- `Layout Grid` — Comparison table grid, what-if scenario cards
- `Layout Panel` — Hero card container, section containers
- `Divider` — Section separators

### Data Display
- `Card` — Hero card, dimension breakdown cards, what-if scenario cards
- `Table` — Comparison matrix with sortable columns
- `Table Cell` — Custom cell rendering for scores, prices, badges
- `Table Header Cell` — Column headers
- `Badge` — Status indicators (Low/Medium/High risk, New, Refurbished, Auction)
- `StatusDot` — Traffic light risk indicators (green/amber/red)
- `ProgressBar` — Score bars for dimensions and overall score
- `Token` — Source tags, category tags
- `Thumbnail` — Vendor logos
- `Metadata List` — Product specs list

### Typography
- `Heading` — Section titles, hero headline
- `Text` — Body text, captions, labels
- `Code` — Monospace numbers (prices, scores, SKUs)

### Actions
- `Button` — Primary (Invoke Savings), Secondary (View Details), Outline (Not Interested)
- `Button Group` — Action button group in hero
- `IconButton` — Export buttons, more actions menu

### Feedback
- `Toast` — Confirmation toasts (savings invoked, report exported)
- `Banner` — Warning banners (no strong alternative, edge cases)
- `Alert Dialog` — Confirm dialog before invoking savings
- `Skeleton` — Loading state while agent researches

### Navigation
- `Breadcrumb` — Report navigation path
- `Tabs` — Tab between Summary / Details / Sources

### Other
- `Icon` — Various icons (check, warning, arrow, export icons)
- `Kbd` — Keyboard shortcuts
- `Collapsible` — Expandable dimension breakdown
- `Overflow List` — Multiple vendor overflow
- `Empty State` — No alternatives found state
- `Lightbox` — Zoom on comparison images

## Export Functionality

### PDF Export
- Uses browser `window.print()` with `@media print` styles
- A4/Letter sized output
- Preserves color coding, tables, and layout
- Clean footer with report ID and timestamp

### Markdown Export
- Generates `.md` file with same structure
- Tables rendered as markdown tables
- Headers as `#` / `##` / `###`
- Code blocks for JSON output
- Downloadable via Blob + anchor click

### CSV Export
- Comparison table exported as CSV
- One row per vendor alternative
- Columns: Vendor, Price, Shipping, Landed, Quality, Speed, Trust, Score, Savings
- Downloadable via Blob + anchor click
