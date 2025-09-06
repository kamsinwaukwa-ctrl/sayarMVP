
# Sayar MVP — Data Dictionary (Fields • Where Collected • Types)

This document maps **every data field** in the MVP to:
- **Where it's collected** (UI step / webhook / system)
- **Postgres type** (PG)
- **API / TypeScript type** (TS)
- **Notes** (validation, defaults, relationships)

> Conventions: All primary/foreign keys are **UUID** (`gen_random_uuid()`). Timestamps are `timestamptz`. Prices are `numeric(12,2)` in NGN (minor-units integer can be a later optimization).

---

## merchants

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on insert | `gen_random_uuid()` |
| name | text | string | Sign‑up form | step 0 | required |
| slug | text unique | string | System | on insert | slugified(name) |
| whatsapp_phone_e164 | text unique | string | Sign‑up form | step 0 | E.164 validation |
| description | text | string | Brand basics | step 1 | optional |
| logo_url | text | string | Brand basics (upload) | step 1 | stored after upload |
| currency | text | 'NGN' | Brand basics | step 1 | ISO code |
| settlement_currency | text | string | Settings | post‑onboarding | default NGN |
| fee_bearer | text | 'merchant' \| 'customer' | Settings | post‑onboarding | check constraint |
| waba_id | text | string | Integrations → WhatsApp | after onboarding | |
| phone_number_id | text | string | Integrations → WhatsApp | after onboarding | |
| meta_app_id | text | string | Integrations → WhatsApp | after onboarding | |
| meta_system_user_token_enc | text | string | Integrations → WhatsApp | after onboarding | encrypted at rest |
| provider_default | text | 'paystack' \| 'korapay' | Connect payments | step 4 | |
| paystack_sk_enc | text | string | Connect payments | step 4 | encrypted |
| paystack_pk_enc | text | string | Connect payments | step 4 | optional |
| korapay_sk_enc | text | string | Connect payments | step 4 | encrypted |
| korapay_pk_enc | text | string | Connect payments | step 4 | optional |
| payments_verified_at | timestamptz | string | System | after verify | null until verified |
| created_at | timestamptz | string | System | on insert | default now() |
| updated_at | timestamptz | string | System | on update | trigger to maintain |

---

## users

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on insert | |
| merchant_id | uuid fk -> merchants | string | System | on invite/sign‑up | owner at sign‑up; staff on invite |
| name | text | string | Sign‑up / Invite | step 0 / invite | |
| email | text unique | string | Sign‑up / Invite | step 0 / invite | validated |
| password_hash | text | string | System | step 0 | hashed (bcrypt/argon2) |
| role | text | 'owner' \| 'staff' | System/UI | step 0 or invite | check constraint |
| created_at | timestamptz | string | System | on insert | |

---

## products

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on create | |
| merchant_id | uuid fk | string | System | on create | |
| title | text | string | Products → Create | step 2 | required |
| description | text | string | Products → Create | step 2 | optional |
| price_ngn | numeric(12,2) | number | Products → Create | step 2 | consider minor units later |
| stock | int | number | Products → Create | step 2 | >=0 |
| reserved_qty | int default 0 | number | System | on reservation | >=0 |
| image_url | text | string | Products → Images | step 2 | first image as primary |
| sku | text | string | Products → Create | step 2 | unique per merchant (recommend) |
| status | text | 'active' \| 'inactive' | Products → Create/Edit | step 2 | |
| catalog_id | text | string | System (Meta sync) | after upsert | Commerce Manager catalog |
| retailer_id | text | string | System | after upsert | stable mapping (UUID/SKU) |
| category_path | text | string | Products → Create | step 2 | 'Hair > Oils' |
| tags | text[] | string[] | Products → Create | step 2 | array of keywords |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## customers

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | first interaction | |
| merchant_id | uuid fk | string | System | first interaction | |
| phone_e164 | text | string | WhatsApp message | on first chat | from `from.phone` |
| name | text | string | Flow / WhatsApp profile | address flow or WA profile | optional |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## addresses

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on save | |
| customer_id | uuid fk -> customers | string | Address Flow / inline | during checkout | |
| label | text | string | Address Flow / inline | during checkout | e.g., "Home" |
| line1 | text | string | Address Flow / inline | during checkout | required |
| lga | text | string | Address Flow / inline | during checkout | from merchant list |
| city | text | string | Address Flow / inline | during checkout | optional |
| state | text | string | Address Flow / inline | during checkout | default "Lagos" if set |
| country | text | string | Address Flow / inline | during checkout | default "NG" |
| is_default | boolean | boolean | System/UI | on save | set true if first |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## delivery_rates

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on create | |
| merchant_id | uuid fk | string | System | on create | |
| name | text | string | Delivery Rates modal | step 3 | |
| areas_text | text | string | Delivery Rates modal | step 3 | CSV or multiline |
| price_ngn | numeric(12,2) | number | Delivery Rates modal | step 3 | >=0 |
| description | text | string | Delivery Rates modal | step 3 | optional |
| active | boolean | boolean | Delivery Rates modal | step 3 | default true |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## orders

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | at checkout start | |
| order_code | text unique | string | System | on insert | human-friendly slug/ulid |
| merchant_id | uuid fk | string | System | on insert | |
| customer_id | uuid fk | string | System | on insert | |
| subtotal_ngn | numeric(12,2) | number | System | before payment | sum of items snapshot |
| shipping_ngn | numeric(12,2) | number | System | before payment | from delivery_rates |
| total_ngn | numeric(12,2) | number | System | before payment | subtotal + shipping |
| status | text | 'pending'\|'paid'\|'failed'\|'cancelled' | System | lifecycle | |
| payment_provider | text | 'paystack'\|'korapay' | System | when creating link | |
| provider_reference | text | string | Provider webhook | on init/update | payment ref |
| wa_message_id | text | string | WA webhook | on order event | for traceability |
| paid_at | timestamptz | string | Provider webhook | on success | nullable |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## order_items

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on insert | |
| order_id | uuid fk -> orders | string | System | on insert | |
| product_id | uuid fk -> products | string | System | on insert | from retailer_id mapping |
| qty | int | number | WA order payload | on order event | >=1 |
| unit_price_ngn | numeric(12,2) | number | Snapshot from product | on order event | |
| total_ngn | numeric(12,2) | number | System | on order event | qty * unit_price |

---

## payments

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on init | |
| order_id | uuid fk -> orders | string | System | on init | |
| provider | text | 'paystack'\|'korapay' | System | on init | |
| reference | text unique | string | Provider | init response/webhook | |
| status | text | 'pending'\|'success'\|'failed' | Provider webhook | on update | |
| amount_ngn | numeric(12,2) | number | System/Provider | on init | equals order total |
| fee_ngn | numeric(12,2) | number | Provider webhook | on update | optional |
| currency | text | string | System | on init | 'NGN' |
| raw | jsonb | any | Provider webhook | on update | full payload |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## webhook_events

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on receipt | |
| source | text | 'wa'\|'paystack'\|'korapay'\|'flows' | Webhook | on receipt | |
| event_key | text unique | string | Webhook | on receipt | idempotency key |
| status | text | 'received'\|'processed'\|'error' | System | lifecycle | |
| raw | jsonb | any | Webhook | on receipt | |
| received_at | timestamptz | string | System | on insert | |
| processed_at | timestamptz | string | System | when done | |

---

## inventory_reservations

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on order event | |
| order_id | uuid fk -> orders | string | System | on order event | |
| product_id | uuid fk -> products | string | System | on order event | |
| qty | int | number | System | on order event | reserved units |
| expires_at | timestamptz | string | System | on order event | now() + 15m |
| status | text | 'active'\|'consumed'\|'released' | System | lifecycle | |
| created_at | timestamptz | string | System | on insert | |

---

## inventory_ledger

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on change | |
| product_id | uuid fk -> products | string | System | on change | |
| delta | int | number | System | sale/release/manual | negative on sale |
| reason | text | 'sale'\|'release'\|'manual' | System | on change | |
| ref_id | uuid \| text | string | System | on change | link to order/reservation |
| created_at | timestamptz | string | System | on insert | |

---

## dlq_events

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on failure | |
| source | text | string | Worker | on failure | e.g., 'catalog_sync' |
| key | text | string | Worker | on failure | |
| reason | text | string | Worker | on failure | error summary |
| payload | jsonb | any | Worker | on failure | |
| created_at | timestamptz | string | System | on insert | |

---

## outbox_events

| Field | PG Type | TS Type | Collected From | When | Notes |
|---|---|---|---|---|---|
| id | uuid pk | string | System | on enqueue | generated in tx |
| merchant_id | uuid fk -> merchants | string | System | on enqueue | routing key |
| job_type | text | 'wa_send'\|'catalog_sync'\|'release_reservation'\|'payment_followup' | System | on enqueue | check constraint |
| payload | jsonb | any | System | on enqueue | job body (idempotent key inside) |
| status | text | 'pending'\|'processing'\|'done'\|'error' | Worker/System | lifecycle | |
| attempts | int | number | Worker | on retry | default 0 |
| max_attempts | int | number | System | on enqueue | default 8 |
| next_run_at | timestamptz | string | System/Worker | schedule | with backoff |
| last_error | text | string | Worker | on failure | nullable |
| created_at | timestamptz | string | System | on insert | |
| updated_at | timestamptz | string | System | on update | |

---

## Cross-entity Derived / Logged IDs (not tables)

- **wa_message_id** (string): from WhatsApp webhook; logged on orders and in structured logs.
- **payment_reference** (string): from provider init/webhook; logged and stored in `payments.reference`.
- **order_code** (text): human-friendly code shown to customers/staff; stored on `orders`.

---

## Validation Highlights

- **E.164**: `whatsapp_phone_e164`, `customers.phone_e164`.
- **Price**: `>= 0`, two decimals; prefer server-side rounding.
- **Stock**: `stock >= reserved_qty >= 0` enforced via application logic and transaction locks.
- **Idempotency**: `webhook_events.event_key` unique; outbox jobs carry internal idempotency keys (e.g., `catalog_sync:{product_id}:{version}`).

---

## Collection Sources Summary

- **Sign‑up wizard**: merchants (name, whatsapp phone), users(owner).
- **Brand basics**: merchants (logo_url, description, currency).
- **Integrations → WhatsApp**: merchants (waba_id, phone_number_id, meta_app_id, token).
- **Connect payments**: merchants (provider_default, *_keys), payments_verified_at.
- **Products → Create/Edit**: products (core fields), images.
- **Delivery rates modal**: delivery_rates.
- **In-chat order**: WA webhook → order_items (qty, mapping via retailer_id), inventory_reservations.
- **Address Flow / inline**: addresses (+ customers.name if provided).
- **Payment**: link creation (payments init); webhook (payments update, orders.paid_at).
- **Workers**: reservation expiry releases, catalog sync via outbox.
