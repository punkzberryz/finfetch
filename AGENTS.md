# AGENTS

## Working Directory Assumption

Unless explicitly stated otherwise, agents should assume the **repository root**
as the working directory when resolving paths.

---

## Tool: finfetch

**finfetch** is a Python-based CLI tool for fetching and processing financial
market data (starting with stock-market news).

The CLI is designed to be safe for automation and for use by agent systems
(e.g. Codex skills).

---

## Authoritative Documents

Before making any changes, agents MUST read and follow:

- Plan: `finfetch/docs/PLANS.md`
- Rules: `finfetch/docs/RULES.md`

These documents define the scope, constraints, and output contracts of finfetch.

---

## Source Code Location

- CLI source code: `finfetch/src/finfetch/`
- CLI entrypoint: `finfetch` (or `python -m finfetch`)

---

## Agent Constraints (Hard Rules)

Agents MUST NOT:

- Break stdout JSON-only output contracts
- Print human-readable text to stdout
- Change output schemas without updating `PLANS.md`
- Add trading, brokerage, or order-execution features

Agents MUST:

- Send logs, progress, and diagnostics to stderr
- Preserve deterministic and versioned outputs
- Validate inputs at the CLI boundary

---

## Allowed Work

Agents MAY:

- Add new `finfetch` subcommands
- Integrate additional financial data sources
- Improve caching, retries, and robustness
- Add or improve tests

---

## Notes

- `stdout` is reserved for machine-readable JSON only
- `stderr` is reserved for logs and progress output
- finfetch is a **data ingestion and processing tool**, not a trading system
