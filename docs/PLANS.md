# finfetch — PLANS

## Purpose

finfetch collects, normalizes, caches, and exports market data for:

- CLI workflows (fetch/export/digest)
- LLM workflows (reading exports directly)
- Local UI to run CLI commands and browse outputs

Key references:

- CLI rules + exports: `docs/RULES_CLI.md`
- UI rules: `docs/RULES_UI.md`
- Output schemas: `docs/SCHEMAS.md`
- Archived design history: `docs/PLANS_ARCHIVE.md`

---

## Todo

- [ ] Node server routes to run `finfetch` CLI commands (any subcommand)
- [ ] Endpoints for commands and export browsing (rich API surface)
- [ ] Transcript scrape robustness: Playwright browser bootstrap helper or offline HTML input fallback for bot-protected pages
- [x] Add `scrape transcript` CLI subcommand for Yahoo Finance transcript links (JSON + Markdown output)
- [x] Persist transcript raw + normalized data in SQLite (new schema for company/date/quarter/speakers/sections/full_text)

## Done

- [x] CLI skeleton + rules enforced (JSON stdout, stderr logs)
- [x] SQLite cache module placeholder
- [x] Implement `fetch fundamentals`, `fetch prices`, `fetch news` using Yahoo library
- [x] Store normalized + raw data in SQLite
- [x] Implement `export` to JSON/CSV/MD
- [x] Establish stable folder conventions
- [x] Implement cache-only digest generators and a high-level orchestrator
- [x] Parallelize per-ticker cache hydration (bounded worker pool, configurable workers)
- [x] Write digest JSON files alongside markdown/CSV/prompt outputs
- [x] Add Finnhub provider and enrichment options (config/env-based)
- [x] Optional sentiment features and broader market digest
- [x] Add a React UI in `apps/ui` using TanStack Start + TypeScript
- [x] Tailwind + shadcn/ui for UI components
- [x] Add Biome linting (`pnpm lint`) for UI
- [x] UI shows CLI stdout JSON and reads from `./exports`
- [x] Home page renders latest daily digest from `exports/digests` and can trigger daily digest generation

---

## Open Questions (shortlist)

- Should portfolio digests use customized headings (e.g., “Portfolio Snapshot”)?
- Should digest prompt customization be exposed as CLI flags?

---

## Near-Term Ideas

- Add CLI endpoints for running any subcommand from the UI.
- Add export browser endpoints for richer UI browsing.
