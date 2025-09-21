# Sayar MVP — Roadmap & Task Order (Themes → Tickets)

> **Legend:**  BE = backend (FastAPI/Supabase/Workers) · FE = frontend (React+Vite+TS)  
> `→` = depends on

---

## Phase 0 — Repo & Tooling (P0)

- [ ] **BE-000 — Monorepo & CI bootstrap**  
  _Deliver:_ repo skeleton (`front/`, `back/`, `migrations/`, `tasks/`), pre-commit, black/ruff/mypy, eslint/prettier, GitHub Actions (lint + BE tests + FE build).
- [ ] **BE-000.1 — Production Deployment & Infrastructure Setup**  
  _Deliver:_ Railway backend deployment, Vercel frontend deployment, environment management, CI/CD pipeline, SSL/HTTPS, monitoring setup, deployment documentation. **Target**: Support 20+ businesses for $15 over 3 months.

---

## Phase 1 — Platform Foundation (P0) → **Gate A: auth working, RLS on, worker alive, error handling robust**

- [ ] **BE-001 — DB schema, UUIDs, kobo, RLS**  
  _Deliver:_ base tables, constraints, indexes, RLS policies on all tenant tables, seed migration.
- [ ] **BE-002 — Secrets & webhook security**  
  _Deliver:_ encrypted key storage, HMAC verify utils (Paystack/Kora), WA verification helper, webhook retry logic.
- [ ] **BE-003 — OpenAPI v0.1 (contracts-first)**  
  _Deliver:_ Swagger for Auth/Merchants/Products/Delivery Rates/Discount validate (stub), **generated TS client** for FE.
- [ ] **BE-003.5 — Roles & RLS Policy Tightening**  
  _Deliver:_ migrate `owner → admin`, enforce roles (`admin`,`staff`), tenant-scoped **SELECT** for admin+staff, restrict **WRITE** (INSERT/UPDATE/DELETE) to **admin only** across tenant tables; update RLS policies accordingly.
- [ ] **BE-004 — Auth & JWT**  
  _Deliver:_ owner/staff, `merchant_id` in JWT, auth dependency enforcing tenant isolation.
- [ ] **BE-005 — Observability v1**  
  _Deliver:_ structured JSON logs, Prometheus counters/histograms, `/healthz`, alerting setup.
- [ ] **BE-006 — Outbox & worker (leader-safe)**  
  _Deliver:_ `outbox_events`, APScheduler worker, `FOR UPDATE SKIP LOCKED`, advisory lock, DLQ.
- [ ] **BE-007 — Error handling & retry framework**  
  _Deliver:_ exponential backoff utils, DLQ processing, webhook retry patterns, circuit breakers.
- [ ] **BE-008 — Rate limiting implementation**  
  _Deliver:_ per-merchant WA message limits, API rate limiting middleware, quota tracking.
- [ ] **BE-009 — Configuration management**  
  _Deliver:_ feature flags system, per-merchant settings, environment-based config loader.
- [ ] **BE-011 — Media upload path & policies** *(moved from Phase 2)*  
  _Deliver:_ buckets for logos/products, size/type validation, RLS policies, signed URL generation.

**Minimal FE to test auth (pulled earlier so you can sign in now):**
- [ ] **FE-000 — App shell + Auth (minimal)** `→ BE-004, BE-003`  
  _Deliver:_ Vite+React+TS shell, Tailwind, React Router, Supabase client bootstrap, **Signup/Login** pages calling BE via generated TS client, `/me` guard page.

- [ ] **FE-000.1 — UI foundations (shadcn/ui reusable component kit)** `→ FE-000, BE-003`  
  _Deliver:_ shadcn/ui setup & tokens; **AppShell primitives** (Sidebar, Header, PageHeader); **Menu** components (TopNav, SidebarNav, DropdownMenu, ContextMenu, Command/CommandPalette); **Form kit** (Form, Input, Select, Textarea, Switch, Combobox integrated with react-hook-form + zod resolver); **Feedback** (Toast, AlertDialog, Dialog, Tooltip, Skeleton); **Data** (Table w/ pagination & sort placeholders, Badge, EmptyState); **Utilities** (`cn`, class‑variance‑authority variants); **Docs**: README + usage examples. _Scope:_ components only (no pages). _Consumers:_ FE-001/FE-002+.

    Add (dev-only showcase):_ add `/_dev/ui` kitchen-sink page to preview all foundation components; route gated by `import.meta.env.DEV` + `VITE_UI_SHOWCASE=true`.

**Gate A = Done when:** Sign up + login works; JWT carries `merchant_id`; RLS prevents cross-tenant reads; worker heartbeats & metrics visible; error handling framework operational; rate limiting active; media upload working.

---

## Phase 2 — Core Commerce Config (P1) → **Gate B: merchant can configure catalog, shipping, payments, WA creds**

- [ ] **BE-010 — Products CRUD + Meta Catalog sync**  
  _Deliver:_ CRUD endpoints, storage signed upload, Graph upsert, `retailer_id` mapping, "visible in Catalog" check.
- [ ] **BE-010.1 — Meta Catalog Feed Endpoint (Multi-Tenant CSV)**  
  _Deliver:_ `/api/v1/meta/feeds/{merchant_slug}/products.csv` endpoint, HTTP caching, merchant isolation, dashboard integration. **Enables**: Zero-friction merchant onboarding with instant feed URLs.
- [ ] **BE-010.2 — Auto-brand & MPN (+ SKU fallback)**  
  _Deliver:_ Default brand from merchant name; auto-generate `mpn` (slug+sku) and `sku` if missing; ensure these flow into product responses and Meta sync payloads.
- [ ] **BE-010.3 — Additional Images in API & Meta Payload**
  _Deliver:_ Expose additional_image_urls[] in ProductResponse; include additional_image_link[] (≤10) in Meta sync payload; update OpenAPI and tests.
- [ ] **BE-012 — Delivery Rates CRUD**  
  _Deliver:_ simple string-match MVP, at least one active rule validation.
- [ ] **BE-013 — Payments: provider verify + key storage**  
  _Deliver:_ verify endpoints (Paystack/Korapay), encrypted storage, mark verified.
- [ ] **BE-014 — Discounts CRUD + validate stub**  
  _Deliver:_ create/pause, validate(time/status/min subtotal/basic usage); **no redemption yet**.
- [ ] **BE-015 — WhatsApp Integrations: verify/save**  
  _Deliver:_ save WABA ID/Phone Number ID/App ID/System User Token (encrypted), “Verify” ping.
- [ ] **BE-016 —  Product Images (Cloudinary): verify/save & upload**  
  _Deliver:_ save cloud_name / api_key / api_secret (encrypted) + base folder; “Verify” ping to Cloudinary Admin API; upload endpoint that returns public, stable HTTPS URLs for image_link; delete endpoint; basic dimension/type validation before upload.
    - [ ] **BE-016.1 — Outbox Sync to Meta**  
      _Deliver:_ when a product’s primary image changes, enqueue a `catalog_sync` outbox event that triggers a Meta Catalog `UPDATE` with the new `image_link`; handle retries, idempotency, and DLQ.  
    - [ ] **BE-016.2 — Transform Presets**  
      _Deliver:_ define Cloudinary transformation presets for consistent quality/size.  
      • Main (Meta): `c_limit,w_1600,h_1600,f_auto,q_auto:good`  
      • Thumb (dashboards): `c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco`  
- [ ] **BE-017 — Re-sync Endpoint Only**  
  _Deliver:_ Deliver: POST /api/v1/products/:id/meta-sync → enqueue job (202, idempotent).
- [ ] **BE-018 — Status API + Reason Normalizer**  
  _Deliver:_ Deliver: derive meta_sync_reason from meta_sync_errors; GET /api/v1/products/:id/meta-sync.
- [ ] **BE-019 — Meta Credentials & Catalog Bootstrap**  
  _Deliver:_ `meta_integrations` table `{ merchant_id, catalog_id, system_user_token, app_id, waba_id? }`; `GET /api/meta/catalog/status` (per merchant) verifies token & catalog access.  
  _Acceptance:_ Secrets stored server-side only; token rotation supported. 200 returns catalog name/id; 401/403 surfaced clearly.
- [ ] **BE-020 — Unpublish on Archive + Admin Unpublish**  
  _Deliver:_ propagate local archive/hide to Meta; POST /api/v1/products/:id/meta-unpublish.  
- [ ] **BE-021 — Meta Reconciliation Cron**  
  _Deliver:_ nightly job to compare local vs Meta state (price, stock, title, image). Auto-enqueue resync jobs for drift and emit metrics (total, drift count, failures).


**FE for merchant setup (forms only, no dashboards yet):**
- [ ] **FE-001 — Onboarding Wizard (steps 1–4)** `→ BE-010/011/012/013/015`  
  _Deliver:_  
  Step 1 Brand basics (logo/desc/currency) → merchants API  
  Step 2 Products (create/edit, image upload) → products API (shows Meta sync status)  
  Step 3 Delivery rates (CRUD) → delivery API  
  Step 4 Payments verify (keys) → payments verify API  
  Integrations tab to **enter & verify WA creds**.

- [ ] **FE-001.1 — Meta Sync UX**  
  _Deliver:_ `MetaSyncStatusPopover` (badge → popover with `status`, `last_synced_at`, `reason`), “Re-sync” row action calling `POST /api/products/:id/meta-sync`, optional fields in product form to improve acceptance (`brand`, `condition`, `gtin/mpn`).

**Gate B = Done when:** Product visible in Meta; delivery rate saved; provider verify OK; WA creds saved & verified; discounts can be created + validate returns true/false.

---

## Phase 3 — WhatsApp Surface (P1) → **Gate C: end-to-end chat experience up to "order event + address/discount"**

- [ ] **BE-022 — Basic WhatsApp webhook + auto-reply** `→ BE-015, BE-007, BE-008`  
  _Deliver:_ webhook verification, message send wrapper, 24h window check, auto-reply with **Browse Catalog / Talk to agent**, error handling.
- [ ] **BE-023 — Flows: Address (Flow-first + inline fallback)**  
  _Deliver:_ flow schema + handler, inline prompts fallback, persist addresses, retry logic.
- [ ] **BE-024 — Flows: Discount mini-flow** `→ BE-014`  
  _Deliver:_ CODE input (Flow) with inline fallback, calls `/discounts/validate`, UX for retry/continue.
- [ ] **BE-025 — Multi-product message & order event** `→ BE-010`  
  _Deliver:_ send multi-product message, map `retailer_id`, receive `messages[].type=="order"` payload, webhook resilience.
- [ ] **BE-026 — WhatsApp error recovery & monitoring** `→ BE-007`  
  _Deliver:_ 24h window enforcement, failed message DLQ, webhook retry patterns, message status tracking.

**(No new FE required here beyond the onboarding forms; testing uses Meta test number + Railway webhook.)**

**Gate C = Done when:** “Hi” auto-reply works; catalog opens in WA; **order event** hits webhook; address flow saves; discount flow validates.

---

## Phase 4 — Orders, Payments & Inventory (P1) → **Gate D: full paid flow; stock & catalog update**

- [ ] **BE-030 — Orders API & state machine**  
  _Deliver:_ create order from WA event, `pending|paid|failed|cancelled`, `order_code` (ULID), totals snapshot fields.
- [ ] **BE-031 — Inventory reservations + expiry**  
  _Deliver:_ atomic reservation (15m TTL), `(order_id, product_id)` unique, expiry worker, concurrency test.
- [ ] **BE-032 — Totals computation**  
  _Deliver:_ subtotal, shipping via delivery rates, **apply one discount**, `total_kobo` checks.
- [ ] **BE-033 — Payment link + webhooks** `→ BE-013/030/032`  
  _Deliver:_ link creation (metadata: `discount_code`, `discount_kobo`), success webhook handling with idempotency.
- [ ] **BE-034 — Inventory decrement & Meta Catalog sync** `→ BE-006`  
  _Deliver:_ on paid: decrement stock, consume reservations, ledger write, enqueue `catalog_sync` outbox jobs.
- [ ] **BE-035 — Discount redemption & limits** `→ BE-014`  
  _Deliver:_ record redemption **only on paid**, enforce total & per-customer limits.
- [ ] **BE-036 — Payment webhook resilience** `→ BE-007, BE-033`  
  _Deliver:_ duplicate detection, failed payment recovery, reconciliation system, idempotency keys.
- [ ] **BE-037 — Inventory stress testing & race condition prevention** `→ BE-031`  
  _Deliver:_ concurrent reservation tests, deadlock prevention, race condition handling, load testing framework.

**(Still no new FE beyond onboarding; we’ll add dashboards next.)**

**Gate D (MVP E2E) = Done when:** chat → catalog → order → reservation → address → (discount) → **payment** → **stock decremented & catalog synced** → confirmation message; **resilient to payment/webhook failures; inventory race conditions prevented**.

---

## Phase 5 — Merchant Dashboard (P1)

- [ ] **FE-002 — Products UI** `→ BE-010/011`  
  _Deliver:_ list + create/edit drawer, image upload, Meta sync badge, stock management.
- [ ] **FE-003 — Delivery Rates UI** `→ BE-012`  
  _Deliver:_ list + modal editor with validations, area management.
- [ ] **FE-004 — Discounts UI** `→ BE-014/035`  
  _Deliver:_ list/create/pause codes; redemption list (when exists), usage analytics.
- [ ] **FE-005a — Orders List & Filters** `→ BE-030`  
  _Deliver:_ paginated order list, status filters, search by order code/customer, date range filters.
- [ ] **FE-005b — Order Detail & Actions** `→ BE-033/034/035`  
  _Deliver:_ order detail view: items, totals, applied discount, payment status, customer info, action buttons.
- [ ] **FE-006 — Customers UI** `→ BE-021`  
  _Deliver:_ list customers, view addresses, order history, contact actions.
- [ ] **FE-007a — WhatsApp & Payment Settings** `→ BE-015/013`  
  _Deliver:_ Integrations (WhatsApp verify), Payments (verify), connection status indicators.
- [ ] **FE-007b — Business Settings & Staff Management** `→ BE-004`  
  _Deliver:_ business info, staff invite/remove, role management, notification preferences.
- [ ] **FE-008 — Basic Analytics Dashboard** `→ BE-030/033`  
  _Deliver:_ conversion metrics, revenue charts, top products, order trends, KPI cards.

---

## Phase 6 — Admin & Ops (P2)

- [ ] **ADM-001 — Sayar Admin panel**  
  _Deliver:_ tenants list, last webhook received, error badges.
- [ ] **ADM-002 — Ops panel** `→ BE-006/034/031`  
  _Deliver:_ stuck reservations, failed catalog syncs, outbox backlog; actions (release reservation, retry sync).
- [ ] **ADM-003 — Events/DLQ viewer** `→ BE-006`  
  _Deliver:_ webhook event history, DLQ payloads with filters.

---

## Phase 7 — QA, Seeds & Demo (P1)

- [ ] **QA-001 — Seed/fixtures**  
  _Deliver:_ script to create pilot merchant, 3 products, 1 delivery rate, 1 discount, test customers.
- [ ] **QA-002 — Event replay harness**  
  _Deliver:_ signed JSON fixtures + CLI to replay WA & Paystack/Kora webhooks, error scenarios.
- [ ] **QA-003 — E2E happy-path test**  
  _Deliver:_ local script that asserts end state (paid order, stock decremented, catalog sync enqueued).
- [ ] **QA-004 — Pilot checklist script**  
  _Deliver:_ auto-verify Gate D acceptance criteria with PASS/FAIL printout.
- [ ] **QA-005 — Error scenario testing suite** `→ BE-007, BE-036, BE-037`  
  _Deliver:_ webhook failures, payment failures, inventory conflicts, network timeouts, recovery validation.
- [ ] **QA-006 — Load testing & stress tests** `→ BE-037`  
  _Deliver:_ concurrent orders, reservation pressure testing, rate limiting validation, performance benchmarks.
- [ ] **QA-007 — End-to-end monitoring validation**  
  _Deliver:_ verify all metrics/alerts work, error tracking, webhook monitoring, outbox health checks.

---

## Post-MVP Backlog (P3 — feature-flagged)

- [ ] **SUP-001 — Chatwoot integration (self-hosted)**
- [ ] **INV-001 — Low-stock alerts (thresholds, email channel, merchant-config)**
- [ ] **GRO-001 — Gamified popups & leads**
- [ ] **GRO-002 — On-site retargeting nudges**

---

## Infrastructure Scaling (P2 — as needed)

- [ ] **INFRA-001 — Multi-Tier Scaling Strategy Implementation** `→ BE-000.1`  
  _Deliver:_ Growth tier setup (Railway Pro + Vercel Pro + CDN), Scale tier setup (multi-region), monitoring and alerting upgrades, cost optimization strategies. **Reference**: `docs/INFRA-001-multi-tier-scaling-strategy.md`

---

## Parallelization & hand-offs (FE/BE lockstep)

- **Phase 1:** FE-000 can start **once** BE-003 (OpenAPI) exists (the generated TS client avoids drift).  
- **Phase 2:** FE-001 onboarding forms can proceed in parallel with BE-010/012/013/015, wired to the **same OpenAPI client**.  
- **Phase 3:** WA work is mostly BE; FE not required. Error handling dependencies established.  
- **Phase 4:** All BE; FE dashboards **not needed** to hit Gate D. Resilience testing critical path.  
- **Phase 5:** FE dashboards consume already-live APIs → fast UI iteration.

---

## What you can test after each Gate

- **Gate A:** Sign up/login; 403/404 isolation checks prove RLS; error handling framework operational; rate limiting active.  
- **Gate B:** Create products, see Meta sync status; save delivery rate; verify payments; save & verify WA creds.  
- **Gate C:** Message test number → auto-reply, open catalog, place WA order (event), address & discount flows; error recovery works.  
- **Gate D:** Payment link → webhook → paid order → stock decrement → catalog sync → confirmation DM; **resilient under failures**; then view orders in FE (Phase 5).
