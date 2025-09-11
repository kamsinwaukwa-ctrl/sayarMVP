---
id: "BE-011"
title: "Media upload (logos only) — path & policies"
owner: "@ai_agent"
status: "planned"
priority: "P0"
theme: "Platform Foundation"
user_story: "As a merchant admin, I want to upload my business logo securely so that my storefront and messages are consistently branded."
labels: ["backend","media","upload","storage","supabase"]
dependencies: ["tasks/BE-001-db-schema-rls.md", "tasks/BE-002-secrets-webhook-security.md"]
created: "2025-01-27"
spec_refs:
  - "sayar_mvp_prd.md#merchant-onboarding"
  - "sayar_mvp_prd.md#tech-stack"
touches:
  - "back/src/api/media.py"
  - "back/src/services/media_service.py"
  - "back/src/utils/storage.py"
  - "storage.rules"
---

# INSTRUCTIONS — READ THIS FIRST WHEN CREATING NEW TASKS

This file is a single, self-contained **TASK** for an AI agent working on Sayar. **One task = one file.**
It is optimized for our stack (FastAPI + Supabase/Postgres + WhatsApp Cloud + Paystack/Korapay + APScheduler Outbox).

Keep scope tight. If a task feels big, split it into multiple task files and list them in `dependencies`.

---

## 1) High-Level Objective
Implement **secure merchant logo upload** with strict validation, private storage, **signed URL** access, and tenant isolation via Supabase Storage policies.

> Scope is **logos only** for Gate A. Future media types (e.g., campaign creatives) will be added in follow-up tasks without breaking this contract.

---

## 2) Background / Context
Branding is required across receipts, dashboards, and outbound messages. We only need a single logo per merchant for Gate A. Files must be private-by-default and accessed via short-lived signed URLs. Storage is Supabase Storage (bucket: `merchant-logos`).

---

## 3) Assumptions & Constraints
- **ASSUMPTION:** Supabase Storage used for file blobs; DB keeps only references if needed.
- **CONSTRAINT:** Only **logo** uploads are allowed in this task.
- **CONSTRAINT:** Objects are **private**; all access via **signed URLs** with TTL.
- **CONSTRAINT:** Tenant isolation enforced using JWT `merchant_id` claim in Storage policies.
- **CONSTRAINT:** Filenames sanitized; normalized to `logo.<ext>` per merchant.
- **CONSTRAINT:** Admins upload/update; Staff may read signed URL. No public access.

---

## 4) Scope
**In:**
- Logo upload endpoint (multipart/form-data)
- File validation (type/size), filename sanitization
- Supabase Storage client utilities
- Signed URL generation
- Storage (RLS) policies for tenant isolation
- Optional: persist `logo_url` on `merchants`

**Out:**
- Product images, campaign creatives (future tasks)
- Image processing (resize/optimize) and CDN
- Public ACLs

---

## 5) API Contract
### POST `/api/v1/media/logo`
**Auth:** `Authorization: Bearer <JWT>` (role: **admin** only)

**Content-Type:** `multipart/form-data`  
**Fields:**
- `file`: `<binary>` (required)

**Response 201:**
```json
{
  "ok": true,
  "data": {
    "url": "https://<storage-origin>/object/private/merchant-logos/<merchant_id>/logo.png",
    "signed_url": "https://<storage-origin>/object/sign/merchant-logos/<merchant_id>/logo.png?...",
    "filename": "logo.png",
    "size": 102400,
    "content_type": "image/png",
    "expires_at": "2025-01-27T11:00:00Z"
  }
}
```

**Errors:** 400 (validation), 401 (unauthenticated), 403 (not admin), 413 (too large), 415 (unsupported type).

---

### GET `/api/v1/media/logo/signed-url`
**Auth:** `Authorization: Bearer <JWT>` (roles: **admin** or **staff**)

**Response 200:**
```json
{
  "ok": true,
  "data": {
    "signed_url": "https://<storage-origin>/object/sign/merchant-logos/<merchant_id>/logo.png?...",
    "expires_at": "2025-01-27T11:00:00Z"
  }
}
```

---

## 6) Data Model & Migration (Postgres, UUIDs, kobo money)
**Tables touched:** `merchants` (optional convenience)

**Optional migration (can be deferred until Postgres is available):**
```sql
-- Add reference column for display convenience (not required for Storage)
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS logo_url text;
```

> The authoritative blob lives in Supabase Storage. `logo_url` is a convenience pointer that can be updated on upload success.

---

## 7) Types & Interfaces
```py
# back/src/models/media.py
from pydantic import BaseModel
from datetime import datetime

ALLOWED_LOGO_TYPES = ["image/jpeg", "image/png", "image/webp"]

class MediaUploadResponse(BaseModel):
    url: str
    signed_url: str
    filename: str
    size: int
    content_type: str
    expires_at: datetime
```

---

## 8) Reliability & Outbox
- **Atomicity:** Write to Storage first; only then update `merchants.logo_url` (if used). On failure, no DB side-effects.
- **Idempotency:** Upload always writes to `merchant-logos/<merchant_id>/logo.<ext>` — re-uploads overwrite safely.
- **Cleanup:** If DB update fails after upload, leave blob in place; next upload overwrites.

---

## 9) Observability (Logs & Metrics)
Emit structured logs:
- `media_upload_start`, `media_upload_success`, `media_upload_failed`
- `signed_url_generated`

Counters:
- `media_uploads_total`, `media_upload_failures_total`
- `signed_urls_generated_total`
- `media_storage_bytes_total`

---

## 10) Security Policies

### Storage Policies (Supabase Storage)
**Bucket:** `merchant-logos` (private)

```sql
-- Example Storage policies (execute in Supabase SQL editor)

-- Admins upload logos to their own folder:
-- Path convention: merchant-logos/<merchant_id>/logo.<ext>
CREATE POLICY "Admins can upload their own logo"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'merchant-logos'
  AND (auth.jwt() ->> 'merchant_id') = (storage.foldername(name))[1]
  AND (auth.jwt() ->> 'role') = 'admin'
);

-- Admins & staff can SELECT (download) their own logo via signed URL creation
CREATE POLICY "Business users can view their own logo"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'merchant-logos'
  AND (auth.jwt() ->> 'merchant_id') = (storage.foldername(name))[1]
  AND (auth.jwt() ->> 'role') IN ('admin','staff')
);

-- Admins can replace/delete their own logo
CREATE POLICY "Admins can delete their own logo"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'merchant-logos'
  AND (auth.jwt() ->> 'merchant_id') = (storage.foldername(name))[1]
  AND (auth.jwt() ->> 'role') = 'admin'
);
```

> Ensure JWT contains `merchant_id` and `role` claims. No “merchant” user role is introduced here; only **admin** and **staff**.

---

## 11) Security
- **Validation:** only `image/png`, `image/jpeg`, `image/webp`; default max size **5MB**.
- **Sanitization:** normalize filename to `logo.<ext>`; reject path traversal.
- **Access Control:** private storage + signed URLs + folder isolation by `merchant_id`.
- **Expiry:** signed URLs short-lived (default 15 minutes).

---

## 12) Environment / Secrets
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (for client-side, if any)
- `SUPABASE_SERVICE_ROLE_KEY` (server-side, for signing URLs if required)
- `SUPABASE_STORAGE_BUCKET=merchant-logos`
- `MEDIA_MAX_SIZE=5242880`  # 5MB
- `MEDIA_ALLOWED_TYPES=image/jpeg,image/png,image/webp`
- `SIGNED_URL_EXPIRY=900`    # 15 minutes

---

## 13) Context Plan
**Beginning (read-only):**
- `back/src/models/database.py`
- `sayar_mvp_prd.md`

**End state (must exist):**
- `back/src/api/media.py`
- `back/src/services/media_service.py`
- `back/src/utils/storage.py`
- `storage.rules`

---

## 14) Ordered Implementation Steps
1) **Model** — `back/src/models/media.py`
   - Pydantic `MediaUploadResponse`, constants (`ALLOWED_LOGO_TYPES`).

2) **Storage Utils** — `back/src/utils/storage.py`
   - Supabase client factory (lazy singleton).
   - `validate_logo(file, max_size, allowed_types)`.
   - `put_logo(merchant_id, file) -> (path, content_type, size)`.
   - `sign_logo_url(merchant_id, ttl_s) -> (signed_url, expires_at)`.

3) **Service** — `back/src/services/media_service.py`
   - `upload_logo(merchant_id, file) -> MediaUploadResponse` (validates, stores, signs).
   - (Optional) update `merchants.logo_url` on success.

4) **API** — `back/src/api/media.py`
   - `POST /api/v1/media/logo` (role=admin)
   - `GET  /api/v1/media/logo/signed-url` (roles=admin|staff)

5) **Policies** — `storage.rules`
   - Include the SQL policies from §10 for Supabase Storage.

6) **Tests (deferred if DB not ready)** — `back/tests/integration/test_media.py`
   - Upload happy-path (logo), validation errors, role checks, signed URL expiry.

---

## 15) Acceptance Criteria
- Admin can upload a logo; response returns URL + signed URL.
- Staff/admin can request a fresh signed URL.
- Files are private and isolated per merchant via policies.
- Validation rejects oversized or unsupported files.
- No “merchant” role is introduced; only **admin** and **staff**.

---

## 16) Testing Strategy (Integration-first)
- **Validation:** wrong MIME, >5MB -> 415/413.
- **AuthZ:** staff cannot upload, can GET signed URL; anonymous denied.
- **Pathing:** uploaded object stored exactly at `merchant-logos/<merchant_id>/logo.<ext>`.
- **Expiry:** signed URL expires as configured.

---

## 17) Manual QA (copy-pasteable)
```bash
# Upload a logo (admin JWT)
curl -X POST http://localhost:8000/api/v1/media/logo   -H "Authorization: Bearer $ADMIN_JWT"   -F "file=@/path/to/logo.png"

# Get signed URL (admin or staff JWT)
curl -X GET http://localhost:8000/api/v1/media/logo/signed-url   -H "Authorization: Bearer $USER_JWT"
```

---

## 18) Rollback Plan
- Remove `media.py` API routes from FastAPI app.
- Remove `media_service.py` and `storage.py` utilities.
- Delete Storage policies related to `merchant-logos` bucket.
- (If created) drop `merchants.logo_url` column.

---

## Notes / Links
- PRD: `sayar_mvp_prd.md#merchant-onboarding`
- Supabase Storage: https://supabase.com/docs/guides/storage
- OWASP File Upload Security: https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
