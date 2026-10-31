# Market Tracker Research — Architecture & API Reference

## Overview / Purpose

**market-tracker-research** is the competitor and market-intelligence research site backing the **Market Tracker** product (live at [elitez-market.streamlit.app](https://elitez-market.streamlit.app/)). Market Tracker is an AI-narrated equity-analytics tool that runs live S&P 500 fundamentals through four Chicago Booth EMBA modules: Corporate Finance (CF), Financial Strategy (FS), Operations Management (OM), and Competitive Strategy (CS).

This repo serves two functions:

1. **Research site** — a static HTML/CSS/JS intelligence dashboard (the "pit-floor terminal") published to GitHub Pages. Five admin views render live competitor data, market-sizing derivations, pricing strategy, whitespace analysis, and design scoring, all sourced from typed JSON files with no build step.
2. **Reusable template / AI pipeline scaffold** — the site is built on the [`competitor-intel-template`](https://github.com/derrick-pixel/competitor-intel-template) ten-agent framework. Methodology files, per-agent invocation prompts, a canonical field dictionary, and a session-prompt archive make the entire research process reproducible and upgradeable by future AI sessions.

**Headline research numbers (Market Tracker 2026):**

| Metric | Value |
|--------|-------|
| TAM    | S$18.0B — global retail-investor research-tools spend |
| SAM    | S$220M — SE-Asia self-directed prosumers + EMBA cohort |
| SOM    | S$6.8M (3-yr cumulative) — Elitez-channel-led capture |
| Competitors catalogued | 30+ (sample data: `sample_data: false`, real project) |
| Top-5 threats | Simply Wall St, Koyfin, Stock Rover, Damodaran NYU XLS, Yahoo Finance |

---

## Tech Stack

| Layer | Technology | Version / Note |
|-------|-----------|----------------|
| Runtime | Vanilla HTML5 + ES2020 modules | No transpiler, no bundler |
| Charts | Chart.js | Vendored as `chart.umd.js` (UMD bundle) |
| PDF export | html2canvas + jsPDF | Vendored; html2canvas rasterises `.pdf-page` divs; jsPDF compiles JPEG pages into A4 |
| Authentication | Supabase JS SDK v2 (CDN) + email OTP | Project `suehogmzjspagcsrqvsw.supabase.co` (ESOP shared project); auth restricted to `elitez.asia` / `dhc.com.sg` via Postgres "Before User Created" hook |
| Fonts | IBM Plex Mono (400–700) + IBM Plex Sans (400–700) | Google Fonts CDN |
| Test runner | Node.js built-in `node:test` | Node 20+ required; `node --test template/assets/js/**/_tests/*.test.mjs` |
| Hosting | GitHub Pages | Repo: `derrick-pixel/market-tracker-research`; live at `derrick-pixel.github.io/market-tracker-research/` |
| Data storage | Static JSON files | No database for live data; Supabase used only for auth gate |

---

## Repository Layout

```
market-tracker-research/
├── index.html                          # Root redirect → template/admin/insights-terminal.html (meta refresh)
├── package.json                        # name, version, test script (node --test); no runtime deps
├── README.md                           # Product brief + headline numbers + stack summary
├── AGENT.md                            # AI-agent briefing: ten-agent roster, workflow, rules
├── METHODS.md                          # Append-only methodology changelog (Agent 7 curates)
├── SESSION-PROMPTS.md                  # Verbatim user-prompt history across 5 build sessions
├── LICENSE                             # MIT
│
├── methodology/                        # Per-agent methodology specs + field dictionary
│   ├── FIELD-DICTIONARY.md             # Canonical schema for all /template/data/*.json fields
│   ├── 00-overview.md                  # Ten-agent workflow diagram + handoff contracts
│   ├── 00-asset-extractor.md           # Agent 0 brief: brand DNA extraction → brand-assets.json
│   ├── 01-competitor-research-analyst.md
│   ├── 02-market-intelligence-analyst.md
│   ├── 03-pricing-strategy-analyst.md
│   ├── 04-whitespace-blue-ocean-analyst.md
│   ├── 05-website-design-auditor.md
│   ├── 06-data-visualization-engineer.md
│   ├── 07-methodology-curator.md       # Mid-flight read-only validator + default pattern-harvester
│   ├── 08-report-generator.md
│   ├── 09-aesthetics-presenter.md
│   └── reference/
│       └── README.md                   # Placeholder for XinceAI whitespace reference PNGs
│
├── prompts/                            # Literal invocation prompts for each agent
│   ├── invoke-asset-extractor.md
│   ├── invoke-competitor-research-analyst.md
│   ├── invoke-market-intelligence-analyst.md
│   ├── invoke-pricing-strategy-analyst.md
│   ├── invoke-whitespace-blue-ocean-analyst.md
│   ├── invoke-website-design-auditor.md
│   ├── invoke-data-visualization-engineer.md
│   ├── invoke-methodology-curator.md
│   ├── invoke-report-generator.md
│   ├── invoke-aesthetics-presenter.md
│   └── extract-new-patterns.md         # Prompt for Agent 7 default-mode post-project harvest
│
└── template/                           # The deployable static site
    ├── index.html                      # Landing page (pit-floor terminal home; product brief + routes list)
    │
    ├── admin/                          # Five intelligence views (auth-gated)
    │   ├── index.html                  # Overview: KPI strip, top-5 threats, full searchable roster
    │   ├── insights-terminal.html      # Pit Floor: TAM/SAM/SOM cascade, persona instruments, tier book
    │   ├── whitespace.html             # Whitespace Atlas: strategy canvas radar, heatmap, attack plans
    │   ├── design-audit.html           # Design Audit: 5-dimension rubric scorecard, design-vs-threat scatter
    │   ├── report.html                 # Board Report: full-bleed PDF synthesis with download
    │   └── assets/js/
    │       └── auth-gate.js            # Drop-in Supabase email-OTP auth overlay
    │
    ├── assets/
    │   ├── css/
    │   │   ├── pit-floor.css           # Shared terminal chrome (status bar, panels, typography)
    │   │   ├── admin.css               # Admin-page overrides
    │   │   ├── dual-theme.css          # Editorial ↔ SaaS theme variables
    │   │   ├── report.css              # PDF report print styles
    │   │   └── site.css                # Public landing page styles
    │   ├── img/
    │   │   ├── favicon.svg
    │   │   ├── favicon-16.png
    │   │   ├── favicon-32.png
    │   │   ├── apple-touch-icon.png
    │   │   └── og-image.png
    │   ├── js/
    │   │   ├── app.js                  # loadAppData(), mountSampleBanner(), mountUnstyledBanner()
    │   │   ├── dom.js                  # h(), clear(), mount() — XSS-safe DOM builder
    │   │   ├── format.js               # fmtSGD(), fmtSGDFull(), fmtRange(), fmtScore(), fmtPct()
    │   │   ├── dual-theme.js           # Editorial ↔ SaaS localStorage theme switcher
    │   │   ├── viz/
    │   │   │   ├── donut.js            # renderMarketDonut() — target-market distribution
    │   │   │   ├── heatmap.js          # renderHeatmap(), renderCellDetail(), cellCount(), cellBand(), buildCellDetail()
    │   │   │   ├── market-funnel.js    # renderMarketFunnel(), buildFunnelData() — TAM/SAM/SOM derivation
    │   │   │   ├── price-bars.js       # renderPriceBars() — horizontal S$/mo bar chart
    │   │   │   ├── radar.js            # buildRadarData(), renderRadar() — strategy canvas
    │   │   │   ├── search.js           # matchesCompetitor(), wireSearch(), debounce()
    │   │   │   └── _tests/
    │   │   │       ├── heatmap.test.mjs
    │   │   │       ├── market-funnel.test.mjs
    │   │   │       ├── radar.test.mjs
    │   │   │       └── search.test.mjs
    │   │   ├── report/
    │   │   │   ├── page-templates.js   # buildSections(), renderPages() — A4 page registry + renderers
    │   │   │   ├── pdf-generator.js    # generatePDF() — Phase-4-validated html2canvas + jsPDF export
    │   │   │   ├── preflight-dom.js    # validateDOM(), formatViolations() — 7-check DOM pre-flight gate
    │   │   │   ├── toc.js              # computePageIndex() — TOC page-number arithmetic
    │   │   │   └── _tests/
    │   │   │       └── toc.test.mjs
    │   │   └── _tests/
    │   │       └── dom.test.mjs
    │   └── vendor/
    │       ├── chart.umd.js            # Chart.js UMD bundle (vendored, no CDN dep in prod)
    │       ├── html2canvas.min.js      # html2canvas (vendored)
    │       └── jspdf.umd.min.js        # jsPDF UMD bundle (vendored)
    │
    └── data/                           # Typed JSON data files (owned by agents; ground truth)
        ├── competitors.json            # Agent 1: competitor records + top_five[] (30+ entries)
        ├── market-intelligence.json    # Agent 2: market sizing + policies + trends
        ├── pricing-strategy.json       # Agent 3: personas + recommended_tiers + grants
        ├── whitespace-framework.json   # Agent 4: strategy_canvas + heatmap + attack_plans
        └── brand-tokens.json           # Agent 9: CSS design tokens (presence = Agent 9 ran)
```

---

## System Architecture

### Components

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                        GitHub Pages (static host)                       │
 │  derrick-pixel.github.io/market-tracker-research/                       │
 │                                                                         │
 │  ┌──────────────┐   meta-refresh   ┌──────────────────────────────────┐ │
 │  │  index.html  │ ─────────────>   │   template/admin/ (5 views)      │ │
 │  │  (root)      │                  │                                  │ │
 │  └──────────────┘                  │  ┌──────────────────────────────┐ │ │
 │                                    │  │ insights-terminal.html       │ │ │
 │  ┌──────────────┐                  │  │ index.html (Overview)        │ │ │
 │  │ template/    │                  │  │ whitespace.html              │ │ │
 │  │ index.html   │                  │  │ design-audit.html            │ │ │
 │  │ (landing)    │                  │  │ report.html                  │ │ │
 │  └──────────────┘                  │  └──────────────────────────────┘ │ │
 │                                    └──────────────────────────────────┘ │
 │          │                                       │                      │
 │          │ fetch() at page load                  │ fetch() at page load │
 │          ▼                                       ▼                      │
 │  ┌──────────────────────────────────────────────────────┐               │
 │  │              template/data/*.json                    │               │
 │  │  competitors.json  market-intelligence.json          │               │
 │  │  pricing-strategy.json  whitespace-framework.json   │               │
 │  │  brand-tokens.json  (brand-assets.json — if Agent 0) │               │
 │  └──────────────────────────────────────────────────────┘               │
 │                                                                         │
 └─────────────────────────────────────────────────────────────────────────┘
          │ Auth gate: OTP email
          ▼
 ┌──────────────────────────────┐
 │  Supabase (suehogmzjspagcsrqvsw)                  │
 │  Project: ESOP shared (asia-southeast1)           │
 │  Auth: email OTP via Resend SMTP                 │
 │  Access policy: elitez.asia + dhc.com.sg only    │
 └──────────────────────────────────────────────────┘
```

### Data Flow

1. Browser loads an admin HTML page.
2. `auth-gate.js` (IIFE, loaded before `</body>`) instantly locks the page (`body.ez-gate-locked`) and checks for an existing Supabase session. If none, it renders an OTP email form as a full-screen overlay. On successful OTP verification, the overlay is removed and `window._sbReady` resolves.
3. Each admin page's inline `<script type="module">` calls `loadAppData()` from `app.js`, which fires four parallel `fetch()` calls to `../data/*.json`.
4. `window.AppData` is set with the resolved JSON quartet `{ competitors, market, pricing, whitespace }`.
5. `mountSampleBanner()` checks `meta.sample_data` on any file; if `true`, prepends a warning banner.
6. `mountUnstyledBanner()` issues a `HEAD` request to `../data/brand-tokens.json`; if the file is absent (Agent 9 has not run), an "Un-styled draft" status banner is prepended.
7. Visualisation modules (`viz/*.js`, `report/*.js`) are imported and render their sections using the `h()` DOM builder from `dom.js` and formatting helpers from `format.js`. Chart.js canvases are populated from loaded data.
8. On `report.html`, clicking the PDF download button calls `generatePDF()`, which runs the 7-check Phase 4 DOM pre-flight (`preflight-dom.js`), then iterates `.pdf-page` elements through `html2canvas` and compiles them into a jsPDF A4 document at JPEG quality 0.62 with compression.

### Brand-state machine (Agent lifecycle)

```
brand-tokens.json absent  ──>  Un-styled draft banner emitted on all admin pages
        │
        │  Agent 9 runs
        ▼
brand-tokens.json present  ──>  Banner suppressed on next page load; pages are re-skinned
```

---

## API Reference

There are no HTTP server routes. The site is a fully static client-side application. All "API surface" is the set of exported JavaScript functions consumed within the browser.

### `template/assets/js/app.js` — Application bootstrap

| Export | Signature | Description |
|--------|-----------|-------------|
| `loadAppData` | `async () => { competitors, market, pricing, whitespace }` | Fetches all four JSON data files in parallel via `Promise.all`. Sets `window.AppData`. Throws on any 4xx/5xx. Called once at page load by each admin page. |
| `mountSampleBanner` | `() => void` | Reads `window.AppData`; prepends a `<div class="sample-data-banner">` to `document.body` if any loaded file has `meta.sample_data === true`. No-op if data not loaded yet. |
| `mountUnstyledBanner` | `async () => void` | HEAD-fetches `../data/brand-tokens.json`. If the file is absent or the request fails, prepends an `<div class="unstyled-draft-banner">` announcing that Agent 9 has not run. |

### `template/assets/js/dom.js` — XSS-safe DOM builder

| Export | Signature | Description |
|--------|-----------|-------------|
| `h` | `(tag: string, props?: object, ...children) => HTMLElement` | Creates an element. `props.class` → `el.className`. `props.style` (object) → `Object.assign(el.style, ...)`. `props.dataset` (object) → `Object.assign(el.dataset, ...)`. `props.onXxx` (function) → `addEventListener`. All text children go through `document.createTextNode` — never `innerHTML`. |
| `clear` | `(node: Node) => void` | Removes all child nodes from `node`. |
| `mount` | `(parent: Node, ...children) => void` | Calls `clear(parent)` then appends children. Skips `null` / `false`. |

### `template/assets/js/format.js` — Display-format helpers

All currency/score/range rendering must use these helpers. Inline formatting is forbidden (flagged by Agent 7 mid-flight pass). Currency prefix is resolved from `window.AppData.market.market_size.currency_label` at runtime, falling back to `"SGD"`.

| Export | Signature | Example output |
|--------|-----------|----------------|
| `fmtSGD` | `(n: number) => string` | `18000000000` → `"S$18B"` · `220000` → `"S$220K"` · `99` → `"S$99"` |
| `fmtSGDFull` | `(n: number) => string` | `48000000` → `"S$48,000,000"` (for tables/appendix) |
| `fmtRange` | `(low, expected, upper: number) => string` | `(19, 39, 79)` → `"S$19 — S$79 (target S$39)"` |
| `fmtScore` | `(n: number, scale: "1-5"\|"0-5"\|"1-10") => string` | `(4.2, "1-10")` → `"4.2 / 10"`. Scale token is mandatory — throws if omitted. |
| `fmtPct` | `(n: number) => string` | `12.5` → `"12.5%"` · `20` → `"20%"` (strips trailing `.0`) |

### `template/assets/js/viz/radar.js` — Strategy canvas

| Export | Signature | Description |
|--------|-----------|-------------|
| `buildRadarData` | `({ dimensions, scores }) => ChartData` | Pure function. Places `"us"` first with thick border (3px) + fill. Other competitors get 1.5px thin lines. Returns Chart.js `{ labels, datasets }`. |
| `renderRadar` | `({ canvas, dimensions, scores, max? }) => Chart` | Mounts a Chart.js radar on `canvas`. `max` defaults to 5. Legend on right. |

### `template/assets/js/viz/heatmap.js` — Whitespace heatmap

| Export | Signature | Description |
|--------|-----------|-------------|
| `cellCount` | `(cell) => number` | Counts competitors with `score >= 3` in the cell. |
| `cellBand` | `(count: number) => "green"\|"amber"\|"red"` | `0–1` → green (whitespace); `2–3` → amber (contested); `4+` → red (crowded). |
| `buildCellDetail` | `({ segmentId, needId, segmentName, needName, cell }) => CellDetail` | Pure: returns `{ headline, band, verdict, ourScore, count, competitors[] }` sorted by score desc then name asc. |
| `renderHeatmap` | `({ container, segments, needs, cells, onCellClick }) => void` | Builds an HTML/CSS-grid heatmap using `h()`. Each cell is colour-banded and emits `onCellClick(detail)` on click. Layout uses `240px repeat(N, 1fr)`. |
| `renderCellDetail` | `(panel: Node, detail: CellDetail) => void` | Renders the cell drill-down panel: verdict badge, headline, scores, competitor list with `specialisation_for_cell`. |

### `template/assets/js/viz/market-funnel.js` — TAM/SAM/SOM derivation cascade

| Export | Signature | Description |
|--------|-----------|-------------|
| `buildFunnelData` | `(marketSize) => FunnelData` | Pure normaliser. If `derivation_flow` and `implications` are absent, returns `legacy_mode: true` (back-compat for old JSON). Otherwise returns `{ stages[], implications[], appendix, sources[], legacy_mode: false }`. |
| `renderMarketFunnel` | `(container: Node, marketSize) => void` | Renders the full three-stage derivation cascade (TAM → SAM → SOM), implications cards, collapsed methodology appendix, and sources line. In legacy mode, renders a plain text fallback. |

### `template/assets/js/viz/search.js` — Competitor search & filter

| Export | Signature | Description |
|--------|-----------|-------------|
| `matchesCompetitor` | `(c, query?, filters?) => boolean` | Pure filter predicate. Text search over `name`, `primary_value_prop`, `hq`, `features`, `strengths`. Filters: `category`, `hqRegion`, `threatLevelMin`. |
| `debounce` | `(fn, ms? = 150) => fn` | Standard 150ms debounce. |
| `wireSearch` | `({ input, filtersEl, competitors, onUpdate }) => void` | Attaches `input` event to search bar and `change` event to filter controls (elements with `name="filter-*"`). Calls `onUpdate(filtered[])` on each change. |

### `template/assets/js/viz/donut.js` — Market distribution chart

| Export | Signature | Description |
|--------|-----------|-------------|
| `renderMarketDonut` | `({ canvas, competitors }) => Chart` | Aggregates `target_market[]` across all competitors, takes top-8, renders Chart.js doughnut. Legend on right. |

### `template/assets/js/viz/price-bars.js` — Price comparison chart

| Export | Signature | Description |
|--------|-----------|-------------|
| `renderPriceBars` | `({ canvas, competitors, ourPriceSgd? }) => Chart` | Horizontal bar chart of `sg_monthly_sgd` for up to 20 competitors. If `ourPriceSgd` is provided, overlays an amber dashed line dataset. |

### `template/assets/js/report/pdf-generator.js` — PDF export

| Export | Signature | Description |
|--------|-----------|-------------|
| `generatePDF` | `async ({ root, data, filename, onProgress? }) => void` | Runs Phase 4 DOM pre-flight (`validateDOM`). On pass, iterates `.pdf-page` divs in `root`, rasterises each with `html2canvas` at scale 2 / JPEG 0.62, compiles into a jsPDF A4 document, calls `pdf.save(filename)`. Throws `PreflightError` on any violation. |
| `PreflightError` | `class extends Error` | Has `.violations: Array<{check, message}>`. Thrown when pre-flight fails. |

### `template/assets/js/report/preflight-dom.js` — DOM pre-flight gate

| Export | Signature | Description |
|--------|-----------|-------------|
| `validateDOM` | `(root: Node, data) => { ok: boolean, violations[] }` | Runs all 7 checks (4a–4g) against rendered `.pdf-page` elements. Never short-circuits — all violations are collected. |
| `formatViolations` | `(violations[]) => string` | Returns `"OK"` or newline-joined `[Phase Nx] message` strings. |

Pre-flight checks:

| Check | What it validates |
|-------|------------------|
| 4a | Canonical section presence (`cover`, `toc`, `exec`, `landscape`, `market`, `pricing`, `ws-thesis`, `ws-heatmap`, `ws-cells`, `website`, `appendix`) and canonical ordering |
| 4b | First page is `data-section="cover"` with class `pdf-cover` and a non-white/non-transparent background |
| 4c | Every non-cover page has a `.pdf-footer` with exactly 3 children (project name, page-of-total, date) |
| 4d | TOC page numbers match the actual rendered page positions for all 7 chapters |
| 4e | Cell Detail Appendix has at least one green and one red row |
| 4f | Appendix page count and row count match `data.competitors.competitors.length` |
| 4g | No empty pages (non-footer text < 50 chars is flagged as blank-page leakage) |

### `template/assets/js/report/page-templates.js` — Report page registry

| Export | Signature | Description |
|--------|-----------|-------------|
| `buildSections` | `(data) => Section[]` | Returns the ordered section registry (cover, toc, exec, landscape, market, pricing, whitespace, design, appendix). Each section has `{ id, title, render, countPages }`. |
| `renderPages` | `(root: Node, sections[], data) => void` | Clears root, computes the TOC page-number index, then calls each section's `render(root, data, ctx)`. |

### `template/assets/js/report/toc.js`

| Export | Signature | Description |
|--------|-----------|-------------|
| `computePageIndex` | `(sections[], data) => { [id]: pageNumber, _total: number }` | Walks sections in order, accumulating page counts via each section's `countPages(data)` callback. Used by TOC renderer and `generatePDF`. |

### `template/admin/assets/js/auth-gate.js` — Supabase auth overlay

This is an IIFE (not an ES module). Drop `<script src="assets/js/auth-gate.js"></script>` before `</body>` on any admin page that requires auth. Depends on `window.supabase` being available (loaded from the Supabase CDN before this script).

**Behaviour:**
- On load: immediately adds `ez-gate-locked` class to `body` (hides all page content via CSS).
- Checks for an existing Supabase session; if found, removes the gate immediately.
- If no session: renders a full-screen OTP overlay (two-stage: email → 6-digit code).
- On successful OTP verification: removes overlay, resolves `window._sbReady`.
- `window._sb` — the Supabase client instance (accessible after gate loads).
- `window._sbReady` — a `Promise<SupabaseClient>` that resolves once the user is authenticated.

**Limitation noted in source**: on pages where data is baked into HTML, the gate hides the rendered UI but not the page source. Moving data to Supabase with RLS is a planned future effort.

---

## Data Model

All data lives in `/template/data/*.json`. Every file opens with a shared `meta` block. `meta.sample_data: false` is required before shipping real-project data.

### Shared `meta` block (all files)

| Field | Type | Description |
|-------|------|-------------|
| `meta.project_name` | string | Human-readable project name |
| `meta.brand_tokens.primary` | string (hex) | Primary brand colour |
| `meta.brand_tokens.secondary` | string (hex) | Secondary brand colour |
| `meta.brand_tokens.accent` | string (hex) | Accent / highlight colour |
| `meta.brand_tokens.neutral_dark` | string (hex) | Dark neutral |
| `meta.brand_tokens.neutral_light` | string (hex) | Light neutral |
| `meta.brand_tokens.font_display` | string | Display typeface CSS value |
| `meta.brand_tokens.font_body` | string | Body typeface CSS value |
| `meta.research_date` | YYYY-MM-DD | Date of last full refresh |
| `meta.sample_data` | boolean | `true` = scaffold placeholder; `false` = real project data |

---

### `competitors.json` (Agent 1)

Top-level: `{ meta, top_five[], competitors[] }`

**`top_five[]`** — curated Top-5 threats:

| Field | Type | Constraint |
|-------|------|-----------|
| `competitor_id` | string | FK → `competitors[].id` |
| `rank` | integer | 1–5 |
| `rationale` | string | ≤ 200 chars |

**`competitors[]`** — full competitor roster (≥ 30 records, ≥ 60% `hq_region ∈ {SEA, APAC}`):

| Field | Type | Allowed / Range |
|-------|------|-----------------|
| `id` | string | lowercase-with-underscores (FK target) |
| `name` | string | Display name |
| `url` | string | Valid URL |
| `category` | string | `global_incumbent` \| `sg_local` \| `regional_challenger` \| `diy_alternative` \| `adjacent` \| `big_si` |
| `hq` | string | "City, Country" |
| `hq_region` | string | `SEA` \| `APAC` \| `Global` \| `Other` (note: `AMER` appears in sample — use `Other` per canonical enum) |
| `target_market` | string[] | Customer segment labels |
| `countries_covered` | string[] | Countries with paying customers |
| `sg_monthly_sgd` | number or null | Singapore list price per month; null if N/A |
| `pricing_range_published` | string | Human-readable price range |
| `pricing_flag` | string | `public` \| `partial` \| `hidden_estimated` |
| `primary_value_prop` | string | ≤ 120 chars |
| `features` | string[] | Notable features |
| `strengths` | string[] | Evidence-anchored strengths |
| `weaknesses` | string[] | Evidence-anchored weaknesses |
| `threat_level` | integer | 1–5 |
| `beatability` | integer | 1–5 |
| `market_share_estimate_pct` | number or null | 0–100; null if not triangulated |
| `research_date` | YYYY-MM-DD | Per-record research date |
| `website_design_rating` | number or null | 1–10; filled by Agent 5 |
| `website_design_notes` | string | ≤ 160 chars; required if any design dimension ≤ 6 |
| `website_screenshot_path` | string | Relative path to desktop screenshot |
| `website_screenshot_path_mobile` | string (optional) | Relative path to 375×667 mobile screenshot |
| `findability_seconds` | object (optional) | `{ pricing, demo, contact }` — each 0–30 or null |
| `implications[]` | object[] (optional) | Per-competitor strategic reads: `{ headline, body, agent_targets[] }` |

---

### `market-intelligence.json` (Agent 2)

Top-level: `{ meta, market_size, policies[], cultural_signals[], economic_signals[], adoption_patterns, trends[] }`

**`market_size`:**

| Field | Type | Notes |
|-------|------|-------|
| `tam_sgd` | number | Numeric TAM in SGD |
| `sam_sgd` | number | Numeric SAM |
| `som_sgd` | number | Numeric SOM |
| `currency_label` | string | Display prefix (`"SGD"`, `"AUD"`, etc.); controls all `fmtSGD()` output |
| `derivation_flow` | object | `{ tam, sam, som }` — each a structured stage block with `stage_label`, `subtitle`, `result_label`, `total_equation`, `filters[]`, `stacks[]` |
| `derivation_flow.<stage>.stacks[]` | object[] | Each: `{ name, source, inputs[{label,value}], equation, result_label }` |
| `implications[]` | object[] | 3–6 cards: `{ headline (≤90), body (≤480), agent_targets[] }` |
| `methodology_appendix` | string | Full derivation prose in a `<details>` block |
| `sources[]` | object[] | `{ title, url }` |

**`policies[]`:** `{ title, body, sentiment ("support"\|"neutral"\|"against"), effective_date, sunset_date?, url, data_as_of, implication_for_us }`

**`cultural_signals[]`:** `{ observation, evidence, implication_for_us }`

**`economic_signals[]`:** `{ indicator, value, source_url, implication_for_us }`

**`adoption_patterns`:** `{ sme_penetration_pct, mnc_penetration_pct, note, country_readiness[{country, regulatory (1-5), tech_maturity (1-5), price_tolerance (1-5)}] }`

**`trends[]`:** `{ title, evidence, implication_for_us }`

---

### `pricing-strategy.json` (Agent 3)

Top-level: `{ meta, personas[], pricing_models[], elasticity_heuristics[], recommended_tiers[], grants[] }`

**`personas[]`** (cap: 5; no two share ≥ 60% of `pains`):

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | FK target |
| `name` | string | Persona display name |
| `icp` | string | Ideal customer profile |
| `pains[]` | string[] | Top pains |
| `current_workaround` | string | How they cope without the product |
| `wtp_band_sgd` | object | `{ low_anchor, expected, upper_stretch }` — all numbers in SGD |
| `nba` | object | Structured NBA: `{ method, summary, inputs, monthly_sgd_equivalent, confidence (0-1) }`. `method` ∈ `wage\|competitor_price\|tooling_stack\|time_value` |
| `whitespace_segment_ids[]` | string[] (optional) | FKs into `whitespace-framework.json → heatmap.segments[].id` |
| `implications[]` | object[] (optional) | Same shape as `market_size.implications[]` |

**`pricing_models[]`:** `{ name, rationale, score_by_persona: { <persona_name>: 1-5 } }`

**`elasticity_heuristics[]`:** `{ segment, elasticity_band ("low"\|"medium"\|"high"), evidence }`

**`recommended_tiers[]`:** `{ name, price_sgd, target_persona, what_in[], what_excluded[], psychological_anchor, effective_price_after_psg }`

**`grants[]`:** `{ name, coverage_pct, cap_sgd, eligibility, applies_to_tiers[] }`

---

### `whitespace-framework.json` (Agent 4)

Top-level: `{ meta, strategy_canvas, heatmap, attack_plans[] }`

**`strategy_canvas`:**

| Field | Type | Notes |
|-------|------|-------|
| `headline_thesis` | string | One-sentence whitespace thesis |
| `dimensions[]` | object[] | `{ key, label }` — up to 8 radar axes (default 8) |
| `scores` | object | Map of `<competitor_id or "us">` → `{ <dim_key>: 0-5 }` |

**`heatmap`:**

| Field | Type | Notes |
|-------|------|-------|
| `segments[]` | object[] | Row axis: `{ id, name, descriptor }` |
| `needs[]` | object[] | Column axis: `{ id, name, short }` |
| `cells` | object | Map keyed `"<segment_id>:<need_id>"` → `{ our_score (0-5), competitors[{id, name, score (0-5), specialisation_for_cell (≤120 chars, pair-specific)}] }` |

**`attack_plans[]`:**

| Field | Type | Notes |
|-------|------|-------|
| `rank` | integer | 1 = top priority |
| `niche_name` | string | **≤ 60 chars** (single-line card headline) |
| `icp` | string | Ideal customer profile for niche |
| `whitespace_segment_id` | string (optional) | FK → `heatmap.segments[].id` |
| `tam_estimate_sgd` | number | Niche TAM |
| `tam_reasoning` | string | Derivation prose |
| `why_gap` | string | Why competitors left this gap |
| `why_we_win` | string | Our differentiator |
| `gtm` | object | `{ channel, pitch, pricing, content }` |

---

### `brand-tokens.json` (Agent 9)

Top-level: `{ meta, extracted_from, tokens, font_imports[], notes }`

| Field | Type | Notes |
|-------|------|-------|
| `extracted_from.type` | string | `public_site` \| `brand_assets_json` \| `manual_override` |
| `extracted_from.reference` | string | URL or file path |
| `extracted_from.captured_at` | YYYY-MM-DD | Capture date |
| `tokens` | object | CSS custom-property values: `bg`, `panel`, `panel_2`, `line`, `line_soft`, `ink`, `dim`, `amber`, `green`, `red`, `cyan`, `maroon`, `primary`, etc. + SaaS-theme variants (`saas_bg`, `saas_ink`, etc.) |
| `font_imports[]` | string[] | Google Fonts URLs to inject into `<head>` |
| `notes` | string | Visual idiom observations |

The presence of this file signals Agent 9 has run and suppresses the "Un-styled draft" banner on all admin pages.

---

### `brand-assets.json` (Agent 0 — optional)

Produced only when the human supplies brand reference materials (PDF deck, Figma, public site). Top-level: `{ meta, source, palette, typography, logo, imagery[] }`. Contains lifted hex values, typeface choices, logo paths, and photography from client materials. Agents 5, 6, 8, and 9 read this file as the project's canonical visual-identity record.

---

## Authentication & Authorization

| Aspect | Detail |
|--------|--------|
| Mechanism | Supabase email OTP (magic-code, 6-digit) |
| Supabase project | `suehogmzjspagcsrqvsw.supabase.co` (shared ESOP project, Singapore region) |
| Domain restriction | `elitez.asia` and `dhc.com.sg` only, enforced by a Postgres "Before User Created" hook on the Supabase project |
| Email delivery | Resend SMTP (from `noreply@elitez.com.sg`) |
| Session storage | `localStorage` (Supabase SDK default) with `persistSession: true`, `autoRefreshToken: true` |
| Scope | All five `template/admin/*.html` pages; `template/index.html` (landing) is public |
| Gate file | `template/admin/assets/js/auth-gate.js` — drop-in IIFE, no module bundling required |
| Known limitation | Gate hides the rendered UI but not the HTML source. Sensitive data baked into HTML is visible to anyone who can view source. Moving data to Supabase with RLS is a documented future item. |

---

## Configuration & Environment Variables

This is a fully static site. There is no server-side runtime and no `.env` file. The only runtime configuration is:

| Config item | Location | Purpose |
|-------------|----------|---------|
| `SUPABASE_URL` | Hard-coded in `template/admin/assets/js/auth-gate.js` | Supabase project endpoint for OTP auth |
| `SUPABASE_ANON_KEY` | Hard-coded in `template/admin/assets/js/auth-gate.js` | Supabase anonymous/public key (safe to expose; RLS enforces access) |
| `meta.brand_tokens` | Each `template/data/*.json` | Per-project brand colours and typography, read by the render layer |
| `meta.sample_data` | Each `template/data/*.json` | `true` = sample banner shown; **must be `false` before shipping** |
| `currency_label` | `template/data/market-intelligence.json → market_size` | Overrides the default `SGD` prefix in all `fmtSGD()` calls (e.g. `AUD`, `HKD`) |
| `brand-tokens.json` existence | `template/data/brand-tokens.json` | Presence/absence controls the un-styled-draft banner at page load |

No API keys, database passwords, or secrets other than the Supabase anon key (which is intentionally public) are present in this repo.

---

## Build, Run & Deployment

### Running locally

No build step. Open any HTML file directly in a browser **served over HTTP** (not `file://`, as ES modules require an origin):

```bash
# From repo root — any static server works:
npx serve market-tracker-research/template
# or:
python3 -m http.server 8080 --directory market-tracker-research/template
```

Then navigate to `http://localhost:8080/admin/insights-terminal.html`.

The `index.html` at the repo root contains a `<meta http-equiv="refresh">` redirecting to `template/admin/insights-terminal.html`, so serving from the repo root also works.

### Running tests

```bash
cd /Users/derrickteo/codings/market-tracker-research
node --test 'template/assets/js/**/_tests/*.test.mjs'
```

Requires Node.js 20+. Tests use `node:test` + `node:assert/strict` with a minimal browser stub injected via `globalThis.document`. No test framework install needed.

Test files and what they cover:

| Test file | Modules tested | Key assertions |
|-----------|---------------|---------------|
| `assets/js/_tests/dom.test.mjs` | `dom.js` | `h()` tag creation, className, text-node XSS safety, event listener wiring, attribute fallback |
| `assets/js/viz/_tests/heatmap.test.mjs` | `viz/heatmap.js` | `cellCount`, `cellBand` banding thresholds, `buildCellDetail` sorting + verdict mapping |
| `assets/js/viz/_tests/radar.test.mjs` | `viz/radar.js` | `buildRadarData` `"us"`-first ordering, dimension ordering, missing-score fill-as-0 |
| `assets/js/viz/_tests/market-funnel.test.mjs` | `viz/market-funnel.js` | Legacy-mode detection, stage normalisation |
| `assets/js/viz/_tests/search.test.mjs` | `viz/search.js` | `matchesCompetitor` text + filter predicates |
| `assets/js/report/_tests/toc.test.mjs` | `report/toc.js` | `computePageIndex` page accumulation |

### Deployment

The site deploys automatically to GitHub Pages on push to `main`:

```
Repository:   derrick-pixel/market-tracker-research
Pages source: main / root (index.html) + template/ subtree
Live URL:     https://derrick-pixel.github.io/market-tracker-research/
```

No CI/CD pipeline is needed — GitHub Pages auto-publishes on push. Because there is no build step, the committed files are the deployed files.

### Updating research data

1. Follow the ten-agent pipeline (`AGENT.md`).
2. Dispatch agents in order: **0 → 1 → 2 → 3 → 4 → 5 → 6 → (7 mid-flight) → 8 → (9 opt-in)**.
3. Each agent writes to its owned slice of `template/data/*.json`.
4. Commit after each agent run: `git add template/data/ && git commit -m "feat: Agent N complete"`.
5. Push: `git push derrick-pixel main`. Pages auto-deploys within ~30–60 seconds.

---

## Notable Implementation Details / Gotchas

### No `innerHTML` anywhere
All DOM construction uses the `h()` helper from `dom.js`. Every string goes through `document.createTextNode`, making XSS from user-supplied competitor data impossible. This is an architectural rule, not a convention — Agent 7 mid-flight mode flags any `innerHTML` or `innerText` setter found in view modules.

### `format.js` helpers are mandatory, not optional
Inline currency formatting (e.g. `'S$' + n.toFixed(0) + 'M'`) is forbidden. The helpers resolve the currency prefix from `window.AppData.market.market_size.currency_label` at runtime, enabling non-SGD projects without code changes. Agent 7 flags inline formatting.

### Un-styled draft banner is file-presence-triggered
The banner in `app.js:mountUnstyledBanner()` is controlled by whether `../data/brand-tokens.json` returns HTTP 200 on a HEAD request. No localStorage flag, no manual dismiss. When Agent 9 writes the file and the page is reloaded, the banner disappears automatically.

### Sample-data banner is JSON-state-triggered
`mountSampleBanner()` checks `meta.sample_data` across all four loaded JSON files. Shipping with `sample_data: true` on any file is a defect (`AGENT.md` rule: "Never ship with `meta.sample_data: true`").

### PDF size budget: 8 MB cap; current settings target < 1 MB
`pdf-generator.js` uses `html2canvas` at `scale: 2` + JPEG quality `0.62` + jsPDF `compress: true` + `'FAST'` image pipeline. The 15-page sample report produces ~800 KB. Auto-downscale tiers are specified in `08-report-generator.md` for projects exceeding the budget.

### Phase 4 DOM pre-flight halts the PDF on structural issues
`validateDOM()` runs all 7 checks before the first `html2canvas` call. A single structural issue (wrong section order, off-by-one TOC page numbers, empty pages, missing footer) throws `PreflightError` with the full violation list. This prevents shipping PDFs with silent layout corruption.

### Supabase anon key is intentionally public
The anon key in `auth-gate.js` is the standard public Supabase key. Domain restriction is enforced server-side by the "Before User Created" Postgres hook on the auth project — the anon key alone cannot bypass it.

### Layout invariants for CSS grid
Per `06-data-visualization-engineer.md` Rule 1: every `display: grid` with mixed fixed-pixel + `1fr` tracks must use `minmax(0, 1fr)` on the `1fr` columns to prevent overflow. Long technical strings in competitor data can break `1fr`-only layouts. The heatmap uses `240px repeat(N, 1fr)` but `overflow-wrap: anywhere` on text cells (Rule 2).

### Agent 7 runs in two distinct modes
- **Default mode** (post-shipment): pattern-harvesting; proposes new methodology entries; writes to `methodology/`. Safe to run at any time.
- **Mid-flight mode** (after Agent 6, before Agent 8): read-only quality-gate validator; produces a violation report at `methodology/proposals/<date>-mid-flight-<slug>.md`; never edits any file.

### `hq_region` enum drift
The sample `competitors.json` uses `"AMER"` for US-headquartered competitors, but the canonical enum in `FIELD-DICTIONARY.md §8` only lists `SEA`, `APAC`, `Global`, `Other`. New agent runs should map Americas HQs to `"Other"`. This is a documented open improvement item (SESSION-PROMPTS.md Session 5, candidate 3).

### Brand tokens dual-theme
`brand-tokens.json` for Market Tracker includes both `theme_mode: "terminal"` tokens (pitch-black pit-floor) and `saas_*` tokens for a hypothetical light SaaS mode. `dual-theme.js` enables switching between `theme-editorial` and `theme-saas` CSS classes on `<body>`, persisted via `localStorage` under key `"elitez-vantage-theme"`.
