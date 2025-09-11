---
id: "BE-009"
title: "Configuration management"
owner: "@ai_agent"
status: "planned"
priority: "P0"
theme: "Platform Foundation"
user_story: "As a developer, I want flexible configuration management so that the platform can adapt to different environments and requirements without code changes."
labels: ["backend","configuration","feature-flags","settings","environment"]
dependencies: ["tasks/BE-001-db-schema-rls.md"]
created: "2025-01-27"
spec_refs:
  - "sayar_mvp_prd.md#tech-stack"
touches:
  - "back/src/config/settings.py"
  - "back/src/config/feature_flags.py"
  - "back/src/api/settings.py"
  - "back/src/models/settings.py"
---

# INSTRUCTIONS — READ THIS FIRST WHEN CREATING NEW TASKS

This file is a single, self-contained **TASK** for an AI agent working on Sayar. **One task = one file.**
It is optimized for our stack (FastAPI + Supabase/Postgres + WhatsApp Cloud + Paystack/Korapay + APScheduler Outbox).

Keep scope tight. If a task feels big, split it into multiple task files and list them in `dependencies`.

---

## 1) High-Level Objective
Implement comprehensive configuration management with feature flags, per-merchant settings, and environment-based configuration loading.

---

## 2) Background / Context (Optional but recommended)
The Sayar platform needs flexible configuration management to support different environments, feature rollouts, and merchant-specific settings. This enables the platform to adapt without code changes and supports A/B testing and gradual feature rollouts.

---

## 3) Assumptions & Constraints
- **ASSUMPTION:** Using Pydantic Settings for configuration
- **CONSTRAINT:** Feature flags must be database-backed
- **CONSTRAINT:** Per-merchant settings must be isolated
- **CONSTRAINT:** Configuration must be environment-specific
- **CONSTRAINT:** All configuration must be validated

---

## 4) Scope
**In:** 
- Environment-based configuration loading
- Feature flags system
- Per-merchant settings management
- Configuration validation
- Configuration API endpoints

**Out:** 
- Complex configuration UI (handled in frontend tasks)
- Configuration analytics (handled in future tasks)
- Advanced feature flag strategies (handled in future tasks)

---

## 5) API Contract (if applicable)

### `GET /api/v1/settings` (auth required)
Response:
```json
{
  "ok": true,
  "data": {
    "feature_flags": {
      "low_stock_alerts": false,
      "advanced_analytics": true
    },
    "merchant_settings": {
      "currency": "NGN",
      "timezone": "Africa/Lagos",
      "notifications_enabled": true
    },
    "system_settings": {
      "maintenance_mode": false,
      "rate_limiting_enabled": true
    }
  }
}
```

### `PATCH /api/v1/settings` (auth required)
Request:
```json
{
  "merchant_settings": {
    "currency": "USD",
    "timezone": "America/New_York",
    "notifications_enabled": false
  }
}
```
Response:
```json
{ "ok": true, "data": { "updated": true } }
```

---

## 6) Data Model & Migration (Postgres, UUIDs, kobo money)

**Tables touched:** `merchants` (for merchant settings association)

**New tables (Postgres / Supabase):**
```sql
-- Feature flags table
CREATE TABLE feature_flags (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    enabled boolean not null default false,
    merchant_id uuid references merchants(id),
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    unique(name, merchant_id)  -- supports global (merchant_id NULL) + per-merchant overrides
);

-- Merchant settings table
CREATE TABLE merchant_settings (
    id uuid primary key default gen_random_uuid(),
    merchant_id uuid not null references merchants(id),
    key text not null,
    value jsonb not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now(),
    unique(merchant_id, key)
);

-- System settings table
CREATE TABLE system_settings (
    id uuid primary key default gen_random_uuid(),
    key text not null unique,
    value jsonb not null,
    description text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);
```

> **Note:** DB test coverage will be addressed after Gate A when the local Postgres instance is introduced. No changes here alter current CI behavior.

---

## 7) Types & Interfaces

`back/src/models/settings.py`
```py
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class SettingType(str, Enum):
    FEATURE_FLAG = "feature_flag"
    MERCHANT_SETTING = "merchant_setting"
    SYSTEM_SETTING = "system_setting"

class FeatureFlag(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    enabled: bool
    merchant_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

class MerchantSetting(BaseModel):
    id: UUID
    merchant_id: UUID
    key: str
    value: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class SystemSetting(BaseModel):
    id: UUID
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SettingsResponse(BaseModel):
    feature_flags: Dict[str, bool]
    merchant_settings: Dict[str, Any]
    system_settings: Dict[str, Any]

class UpdateSettingsRequest(BaseModel):
    merchant_settings: Optional[Dict[str, Any]] = Field(default=None)
```

---

## 8) Reliability & Outbox
- **Configuration caching:** Cache configuration reads to reduce DB load (TTL via env).
- **Configuration validation:** All updates validated via Pydantic.
- **Configuration rollback:** Ability to flip flags or restore previous JSON values as needed (manual for MVP).

---

## 9) Observability (Logs & Metrics)
Structured logs:
- `config_loaded`, `config_updated`, `config_validation_failed`
- `feature_flag_enabled`, `feature_flag_disabled`

Metrics:
- `config_updates_total`
- `feature_flag_changes_total`
- `config_validation_failures_total`

---

## 10) Security Policies
- Only authenticated/authorized users (admin or staff roles where applicable) can update settings.
- All inputs validated and sanitized.
- Record audit logs for changes (log actor, keys, old vs new, timestamp).

---

## 11) Security
- Role-based access (admin vs staff).
- Strict schema validation to prevent malformed config from entering system.
- No secrets stored in these tables (env/secrets remain in secure env management).

---

## 12) Environment / Secrets
- `CONFIG_CACHE_TTL` — Configuration cache TTL in seconds
- `FEATURE_FLAGS_ENABLED` — Enable/disable feature flag checks globally (bool)
- `CONFIG_VALIDATION_STRICT` — Strict configuration validation; if true, reject unknown keys

---

## 13) Context Plan
**Beginning (read-only):**
- `back/src/models/database.py` _(read-only)_
- `sayar_mvp_prd.md` _(read-only)_

**End state (must exist after completion):**
- `back/src/config/settings.py`
- `back/src/config/feature_flags.py`
- `back/src/api/settings.py`
- `back/src/models/settings.py`

---

## 14) Ordered Implementation Steps
1. **Configuration Models** — `back/src/models/settings.py`
   - Pydantic models for feature flags, merchant settings, system settings.

2. **Configuration Loading** — `back/src/config/settings.py`
   - Pydantic `BaseSettings` for env + defaults.
   - Validation + caching (in-memory with TTL).

3. **Feature Flags** — `back/src/config/feature_flags.py`
   - `is_feature_enabled(name, merchant_id=None)`.
   - Cache lookups with TTL and simple in-memory store.
   - Support global and per-merchant overrides.

4. **Settings API** — `back/src/api/settings.py`
   - `GET /api/v1/settings` (return merged view for caller's merchant).
   - `PATCH /api/v1/settings` (update caller's merchant settings subset).
   - Basic role checks and validation.

5. **Integration**
   - Wire routes into FastAPI app.
   - Ensure settings module is loaded at startup.

6. **Tests** — `back/tests/integration/test_settings.py`
   - Loading, flags, and API behaviors.
   - (DB-dependent tests deferred until Postgres is available post–Gate A.)

---

## 15) Acceptance Criteria
- Env-based config loads correctly and is validated.
- Feature flags return correct state for global and merchant contexts.
- Per-merchant settings are isolated and retrievable via API.
- Settings update endpoint validates and persists changes.
- Logs & metrics emitted on load/update and flag changes.

---

## 16) Testing Strategy (Integration-first)
- Test configuration loading from env.
- Test feature flag checks (with/without merchant).
- Test settings API happy paths and validation failures.
- (Postgres-backed tests to be enabled after Gate A.)

---

## 17) Manual QA (copy-pasteable)
```bash
# Read settings
curl -s -X GET http://localhost:8000/api/v1/settings   -H "Authorization: Bearer $JWT" | jq

# Update merchant settings (example)
curl -s -X PATCH http://localhost:8000/api/v1/settings   -H "Authorization: Bearer $JWT"   -H "Content-Type: application/json"   -d '{
        "merchant_settings": {
          "currency": "USD",
          "timezone": "America/New_York",
          "notifications_enabled": false
        }
      }' | jq

# Quick check of a feature flag
python - <<'PY'
from back.src.config.feature_flags import is_feature_enabled
print('low_stock_alerts ->', is_feature_enabled('low_stock_alerts'))
PY
```

---

## 18) Rollback Plan
- Remove settings API routes and handlers.
- Remove feature flags module.
- Remove settings loader module.
- Revert configuration tables (DDL).

---

## Notes / Links
- PRD: `sayar_mvp_prd.md#tech-stack`
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Feature Toggles: https://martinfowler.com/articles/feature-toggles.html
