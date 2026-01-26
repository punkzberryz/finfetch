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

## Milestones

M0 — Scaffolding [DONE]

- [x] CLI skeleton + rules enforced (JSON stdout, stderr logs)
- [x] SQLite cache module placeholder

M1 — Yahoo Finance v0 [DONE]

- [x] Implement `fetch fundamentals`, `fetch prices`, `fetch news` using Yahoo library
- [x] Store normalized + raw data in SQLite

M2 — Export Pipeline [DONE]

- [x] Implement `export` to JSON/CSV/MD
- [x] Establish stable folder conventions

M3 — Digest (Weekly/Daily) [DONE]

- [x] Implement cache-only digest generators and a high-level orchestrator
- [x] Parallelize per-ticker cache hydration (bounded worker pool, configurable workers)
- [x] Write digest JSON files alongside markdown/CSV/prompt outputs

M4 — Finnhub Add-on [DONE]

- [x] Add Finnhub provider and enrichment options (config/env-based)
- [x] Optional sentiment features and broader market digest

M5 — Local UI (TanStack Start) [IN PROGRESS]

- [x] Add a React UI in `apps/ui` using TanStack Start + TypeScript
- [x] Tailwind + shadcn/ui for UI components
- [x] Add Biome linting (`pnpm lint`) for UI
- [ ] Node server routes to run `finfetch` CLI commands (any subcommand)
- [x] UI shows CLI stdout JSON and reads from `./exports`
- [ ] Endpoints for commands and export browsing (rich API surface)
- [x] Home page renders latest daily digest from `exports/digests` and can trigger daily digest generation

---

## Open Questions (shortlist)

- Should portfolio digests use customized headings (e.g., “Portfolio Snapshot”)?
- Should digest prompt customization be exposed as CLI flags?

---

## Near-Term Ideas

- Add CLI endpoints for running any subcommand from the UI.
- Add export browser endpoints for richer UI browsing.
