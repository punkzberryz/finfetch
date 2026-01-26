# finfetch — RULES

Authoritative and non-optional. This file is the index; follow the relevant sub-rules for the work you are doing.

---

## 1) Core (Applies to All Work)

- Do not break existing output contracts.
- Do not add trading, brokerage, or order-execution features.
- Deterministic behavior is required for the same inputs (excluding timestamps).
- Sensitive data (API keys, secrets) MUST NOT be logged or exposed.

---

## 2) CLI Rules

For any CLI changes (commands, output, data ingestion, exports), follow:

- `docs/RULES_CLI.md`
- `docs/SCHEMAS.md` (output envelopes and error types)

---

## 3) UI Rules

For any UI changes (frontend, dashboards, viewers), follow:

- `docs/RULES_UI.md`
