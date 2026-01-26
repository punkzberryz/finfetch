# finfetch — SCHEMAS

This document defines the authoritative JSON output shapes for the CLI.

---

## 1) Output Envelope (Required)

All CLI responses MUST use one of the following envelopes.

### Success

    {
      "ok": true,
      "data": { ... },
      "meta": { "version": 1 }
    }

### Error

    {
      "ok": false,
      "error": {
        "type": "ValidationError | NetworkError | RateLimitError | ProviderError | UnknownError",
        "message": "Human-readable summary",
        "details": { }
      },
      "meta": { "version": 1 }
    }

Rules:

- No stack traces in `stdout`
- `error.type` MUST be stable and predictable
- Sensitive information MUST NOT appear in errors

---

## 2) Error Types (Stable)

`error.type` MUST be one of:

- `ValidationError`
- `NetworkError`
- `RateLimitError`
- `ProviderError`
- `UnknownError`

---

## 3) Versioning

- `meta.version` MUST be present and integer.
- Schema changes MUST increment `meta.version`.
- Backwards-incompatible changes require updating `docs/PLANS.md`.
