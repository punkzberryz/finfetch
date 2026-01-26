# finfetch — UI RULES

Authoritative and non-optional for UI work.

---

## 1) Data Access & Contracts

- UI MUST NOT call external market data APIs directly; it uses the local CLI outputs or cache.
- UI MUST NOT attempt trading, brokerage, or order execution actions.
- UI MUST treat CLI output envelopes as the source of truth; handle `ok=false` errors gracefully.

---

## 2) Determinism & Reproducibility

- UI MUST render deterministic views for the same inputs and dataset.
- Sorting and grouping MUST be explicit and stable.

---

## 3) Security & Privacy

- API keys and secrets MUST NOT be stored in client-side code.
- UI MUST NOT log or display sensitive data.

---

## 4) Export Awareness

- UI MAY read from `./exports` and show deterministic file paths.
- UI MUST NOT mutate export files unless explicitly designed as an editor.

---

## 5) Dev Server (Workflow)

- Assume `pnpm dev` is running in the background during UI development.
- Do NOT stop or restart the dev server unless explicitly requested.
- Use `pnpm` for installing UI dependencies.

---

## 6) Quality Gates

- Run `pnpm lint` in `apps/ui` after UI code changes.

## 7) User Notifications

- Use `react-toastify` for all transient user feedback (success messages, non-blocking errors, status updates).
