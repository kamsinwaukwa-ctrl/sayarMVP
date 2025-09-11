---
id: "FE-000"
title: "App shell + Auth (minimal)"
owner: "@ai_agent"
status: "planned"
priority: "P0"
theme: "Platform Foundation"
user_story: "As a merchant, I want to sign up and log in to access my store dashboard so that I can manage my business."
labels: ["frontend","react","auth","vite","tailwind"]
dependencies: ["tasks/BE-003-openapi-contracts.md", "tasks/BE-004-auth-jwt.md"]
created: "2025-01-27"
spec_refs:
  - ".cursor/rules/PRD.mdc#merchant-onboarding"
  - ".cursor/rules/PRD.mdc#tech-stack"
touches:
  - "front/src/app/App.tsx"
  - "front/src/pages/auth/Login.tsx"
  - "front/src/pages/auth/Signup.tsx"
  - "front/src/pages/dashboard/Dashboard.tsx"
  - "front/src/hooks/useAuth.ts"
  - "front/src/lib/api-client.ts"
  - "front/src/components/auth/"
---

# INSTRUCTIONS — READ THIS FIRST WHEN CREATING NEW TASK

This file is a single, self-contained **TASK** for an AI agent working on Sayar. **One task = one file.**
It is optimized for our stack (FastAPI + Supabase/Postgres + WhatsApp Cloud + Paystack/Korapay + APScheduler Outbox).

Keep scope tight. If a task feels big, split it into multiple task files and list them in `dependencies`.

---

## 1) High-Level Objective
Create a minimal React app shell with authentication (signup/login) that can communicate with the backend API and provide a basic dashboard for merchants.

---

## 2) Background / Context (Optional but recommended)
The Sayar platform needs a frontend application for merchants to access their store dashboard. This task establishes the basic app structure with authentication using the generated TypeScript client from the backend API.

---

## 3) Assumptions & Constraints
- **ASSUMPTION:** Using React 18 with Vite and TypeScript
- **CONSTRAINT:** Use Tailwind CSS for styling
- **CONSTRAINT:** Use React Router for navigation
- **CONSTRAINT:** Use generated TypeScript client for API calls
- **CONSTRAINT:** JWT tokens are set by the backend in **secure HTTP-only cookies** (front-end does **not** store tokens)
- **CONSTRAINT:** Support our business user roles **'admin'** and **'staff'** (no 'merchant' role)

---

## 4) Scope
**In:** 
- React app shell with routing
- Authentication pages (signup/login)
- Basic dashboard page
- Auth context and hooks
- API client integration
- Protected route guards

**Out:** 
- Complex dashboard features (handled in future tasks)
- Advanced authentication features (handled in future tasks)
- Admin interface for SEA staff (handled later)

---

## 5) API Contract (if applicable)
**Generated TypeScript Client (from BE-003):**
```ts
// Generated from OpenAPI spec
export interface AuthRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
  business_name: string;
  whatsapp_phone_e164: string;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'staff';
  merchant_id: string;
}

export interface AuthResponse {
  user: AuthUser;
}
```

**Notes**
- The backend (BE-004) returns `Set-Cookie` with the JWT (HttpOnly, Secure, SameSite=lax/strict as configured). Frontend sends cookies with `credentials: 'include'` and **never** reads/stores the token.
- If CSRF is enabled on the backend, the frontend sends an `X-CSRF-Token` header as provided by the backend (e.g., non-HttpOnly cookie or bootstrap endpoint).

---

## 6) Data Model & Migration (Postgres, UUIDs, kobo money)
N/A — Frontend only.

---

## 7) Types & Interfaces (if applicable)
```ts
// front/src/types/auth.ts
export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'staff';
  merchant_id: string;
}

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

// front/src/types/api.ts
export interface ApiResponse<T = any> {
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  timestamp: string;
}
```

---

## 8) Reliability & Outbox
N/A — Frontend only.

---

## 9) Observability (Logs & Metrics)
- **Error logging:** Log authentication errors (console + pluggable reporter)
- **Performance tracking:** Track route transitions (TBT/LCP optional later)
- **User analytics:** Track login/signup success/failure events (stub)

---

## 10) Security Policies
- **JWT storage:** Only as **HttpOnly** cookie (set by backend)
- **CSRF protection:** Send `X-CSRF-Token` when provided by backend
- **Input validation:** Client-side form validation with graceful errors
- **XSS prevention:** No innerHTML; sanitize any user-provided strings

---

## 11) Security
- **JWT handling:** Use `credentials: 'include'` on all API calls
- **Role awareness:** App shell displays correct nav for `admin` vs `staff`
- **Route guards:** Redirect unauthenticated users to `/login`

---

## 12) Environment / Secrets
Required env:
- `VITE_API_BASE_URL` — Backend API base URL
- `VITE_APP_NAME` — Application name
- `VITE_APP_VERSION` — Application version

---

## 13) Context Plan
**Beginning (add these to the agent's context; mark some read-only):**
- `front/.cursor/rules/` _(read-only)_
- `sayar_mvp_prd.md` _(read-only)_

**End state (must exist after completion):**
- `front/src/app/App.tsx`
- `front/src/pages/auth/Login.tsx`
- `front/src/pages/auth/Signup.tsx`
- `front/src/pages/dashboard/Dashboard.tsx`
- `front/src/hooks/useAuth.ts`
- `front/src/lib/api-client.ts`
- `front/src/components/auth/`

---

## 14) Ordered Implementation Steps
1. **Project Setup** — Initialize React app with Vite
   - Install dependencies (React, TypeScript, Tailwind, React Router)
   - Configure Vite and Tailwind
   - Add `.env` with `VITE_API_BASE_URL`

2. **API Client** — Set up generated client
   File: `front/src/lib/api-client.ts`
   - Import generated OpenAPI client
   - Set `baseURL` from `VITE_API_BASE_URL`
   - Always use `credentials: 'include'`
   - Optional: attach `X-CSRF-Token` from meta/JS variable if provided

3. **Auth Context** — Create authentication context
   File: `front/src/hooks/useAuth.ts`
   - `AuthProvider` holds `user` + `loading`
   - `login`, `register`, `logout` call API via generated client
   - `bootstrap` endpoint loads current user on app start (cookies only)

4. **Auth Components** — Auth UI
   Dir: `front/src/components/auth/`
   - `LoginForm`: email/password
   - `SignupForm`: name/email/password + business_name + whatsapp_phone_e164
   - `ProtectedRoute`: wraps children; redirects to `/login` if not authed

5. **Auth Pages**
   Dir: `front/src/pages/auth/`
   - `Login.tsx` uses `LoginForm`
   - `Signup.tsx` uses `SignupForm`
   - Minimal, clean Tailwind UI

6. **Dashboard Page**
   File: `front/src/pages/dashboard/Dashboard.tsx`
   - Shows welcome, user role, merchant name (if present), and quick links

7. **App Shell**
   File: `front/src/app/App.tsx`
   - Router, routes
   - `AuthProvider` at root
   - Nav with app name, user menu, logout
   - `ProtectedRoute` around `/dashboard`

8. **Tests**
   Dir: `front/src/__tests__/`
   - Auth hook tests (login/logout state)
   - Protected route behavior
   - Form validation

---

## 15) Acceptance Criteria
- Users can **sign up** with business info and **log in**
- Backend sets JWT cookie; app uses **credentials include** on requests
- **Admin** and **staff** can access dashboard (content may differ slightly)
- **Protected routes** require authentication
- Proper client-side **validation** and **error handling**
- API client works against BE endpoints defined in BE-003 / BE-004

---

## 16) Testing Strategy (Integration-first)
- Test authentication flow (happy + failure paths)
- Test protected route redirect when unauthenticated
- Test role rendering differences in app shell (admin vs staff)
- Test form validation (invalid emails, weak passwords, etc.)

---

## 17) Manual QA (copy-pasteable)
```bash
# Start dev server
cd front
npm install
npm run dev

# Register via UI: http://localhost:5173/signup
# Login via UI: http://localhost:5173/login

# (Optional) verify API calls include cookies
# In devtools Network tab, confirm 'Cookie' is sent and Set-Cookie received.
```

---

## 18) Rollback Plan
- Remove auth context, pages, and protected routes
- Remove generated API client integration
- Revert to a basic Vite React template

---

## Notes / Links
- PRD: `.cursor/rules/PRD.mdc#merchant-onboarding`
- React Router: https://reactrouter.com/
- Tailwind CSS: https://tailwindcss.com/
- Vite: https://vitejs.dev/
