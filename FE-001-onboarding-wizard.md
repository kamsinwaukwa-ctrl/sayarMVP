---
id: "FE-001"
title: "Onboarding Wizard (steps 1–4)"
owner: "@ai_agent"
status: "planned"
priority: "P1"
theme: "Core Commerce Config"
user_story: "As a new merchant, I want to complete a guided onboarding process so that I can set up my store and start selling on WhatsApp."
labels: ["frontend","react","onboarding","forms","wizard"]
dependencies: ["tasks/BE-010-products-crud-meta-sync.md", "tasks/BE-011-media-upload-policies.md", "tasks/BE-012-delivery-rates-crud.md", "tasks/BE-013-payments-provider-verify.md", "tasks/BE-015-whatsapp-integrations-verify.md"]
created: "2025-01-27"
spec_refs:
  - "sayar_mvp_prd.md#merchant-onboarding"
touches:
  - "front/src/pages/onboarding/"
  - "front/src/components/onboarding/"
  - "front/src/hooks/useOnboarding.ts"
  - "front/src/lib/onboarding.ts"
---

# INSTRUCTIONS — READ THIS FIRST WHEN CREATING NEW TASK

This file is a single, self-contained **TASK** for an AI agent working on Sayar. **One task = one file.**
It is optimized for our stack (FastAPI + Supabase/Postgres + WhatsApp Cloud + Paystack/Korapay + APScheduler Outbox).

Keep scope tight. If a task feels big, split it into multiple task files and list them in `dependencies`.

---

## 1) High-Level Objective
Create a comprehensive onboarding wizard with 4 steps that guides new merchants through setting up their store, products, delivery rates, payments, and WhatsApp integration.

---

## 2) Background / Context (Optional but recommended)
The Sayar platform needs a user-friendly onboarding experience for new merchants to set up their store quickly and efficiently. This wizard will guide them through all the essential configuration steps to get started.

---

## 3) Assumptions & Constraints
- **ASSUMPTION:** Using React Hook Form for form management
- **CONSTRAINT:** Use Zod for form validation
- **CONSTRAINT:** Use React Query for API calls
- **CONSTRAINT:** Use Tailwind CSS for styling
- **CONSTRAINT:** Wizard must be responsive and accessible

---

## 4) Scope
**In:** 
- 4-step onboarding wizard
- Step 1: Brand basics (logo, description, currency)
- Step 2: Products (create/edit, image upload)
- Step 3: Delivery rates (CRUD)
- Step 4: Payments verification (keys)
- Integrations tab for WhatsApp credentials

**Out:** 
- Advanced onboarding features (handled in future tasks)
- Onboarding analytics (handled in future tasks)
- Custom onboarding flows (handled in future tasks)

---

## 5) API Contract (if applicable)
**Generated TypeScript Client:**
```ts
// Generated from OpenAPI spec
export interface UpdateMerchantRequest {
  name?: string;
  description?: string;
  logo_url?: string;
  settlement_currency?: string;
}

export interface CreateProductRequest {
  title: string;
  description?: string;
  price_kobo: number;
  stock: number;
  sku: string;
  category_path?: string;
  tags?: string[];
}

export interface CreateDeliveryRateRequest {
  name: string;
  areas_text: string;
  price_kobo: number;
  description?: string;
}

export interface VerifyPaymentRequest {
  provider: 'paystack' | 'korapay';
  secret_key: string;
  public_key: string;
  set_as_default: boolean;
}

export interface VerifyWhatsAppRequest {
  waba_id: string;
  phone_number_id: string;
  app_id: string;
  system_user_token: string;
}
```

---

## 6) Data Model & Migration (Postgres, UUIDs, kobo money)
N/A - This is frontend implementation

---

## 7) Types & Interfaces (if applicable)
```ts
// front/src/types/onboarding.ts
export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  required: boolean;
}

export interface OnboardingData {
  step1: {
    business_name: string;
    description: string;
    logo_url?: string;
    currency: string;
  };
  step2: {
    products: CreateProductRequest[];
  };
  step3: {
    delivery_rates: CreateDeliveryRateRequest[];
  };
  step4: {
    payment_provider: 'paystack' | 'korapay';
    payment_verified: boolean;
  };
  integrations: {
    whatsapp_verified: boolean;
    whatsapp_credentials?: VerifyWhatsAppRequest;
  };
}

export interface OnboardingContextType {
  currentStep: number;
  data: OnboardingData;
  updateStep: (step: number) => void;
  updateData: (step: keyof OnboardingData, data: any) => void;
  completeStep: (step: number) => void;
  isStepCompleted: (step: number) => boolean;
  canProceed: (step: number) => boolean;
  submitOnboarding: () => Promise<void>;
  loading: boolean;
  error: string | null;
}
```

---

## 8) Reliability & Outbox
N/A - This is frontend implementation

---

## 9) Observability (Logs & Metrics)
- **User analytics:** Track onboarding completion rates
- **Error logging:** Log onboarding errors
- **Performance tracking:** Track step completion times

---

## 10) Security Policies
- **Form validation:** Client-side validation for all forms
- **Data sanitization:** Sanitize all user inputs
- **Secure storage:** Store sensitive data securely

---

## 11) Security
- **Input validation:** Zod validation for all forms
- **XSS prevention:** Proper input sanitization
- **CSRF protection:** CSRF tokens for API calls

---

## 12) Environment / Secrets
Required env:
- `VITE_API_BASE_URL` - Backend API base URL
- `VITE_STORAGE_BUCKET` - Supabase storage bucket

---

## 13) Context Plan
**Beginning (add these to the agent's context; mark some read-only):**
- `front/.cursor/rules/` _(read-only)_
- `sayar_mvp_prd.md` _(read-only)_

**End state (must exist after completion):**
- `front/src/pages/onboarding/OnboardingWizard.tsx`
- `front/src/components/onboarding/`
- `front/src/hooks/useOnboarding.ts`
- `front/src/lib/onboarding.ts`

---

## 14) Ordered Implementation Steps
1. **Onboarding Types** — Create onboarding types
   File: `front/src/types/onboarding.ts`
   - Onboarding data models
   - Step definitions
   - Context types

2. **Onboarding Hook** — Create onboarding context hook
   File: `front/src/hooks/useOnboarding.ts`
   - Onboarding state management
   - Step navigation logic
   - Data persistence

3. **Onboarding Components** — Create step components
   Files: `front/src/components/onboarding/`
   - Step1BrandBasics.tsx
   - Step2Products.tsx
   - Step3DeliveryRates.tsx
   - Step4Payments.tsx
   - IntegrationsTab.tsx

4. **Onboarding Wizard** — Create main wizard component
   File: `front/src/pages/onboarding/OnboardingWizard.tsx`
   - Wizard layout
   - Step navigation
   - Progress indicator

5. **Onboarding Utils** — Create utility functions
   File: `front/src/lib/onboarding.ts`
   - Validation functions
   - Data transformation
   - API integration

6. **Tests** — Create onboarding tests
   Files: `front/src/__tests__/onboarding/`
   - Component tests
   - Hook tests
   - Integration tests

---

## 15) Acceptance Criteria
- Onboarding wizard has 4 clear steps
- Each step has proper validation
- Data persists between steps
- API integration works correctly
- Responsive design works on all devices
- Accessibility requirements are met
- Error handling works properly

---

## 16) Testing Strategy (Integration-first)
- Test onboarding flow end-to-end
- Test form validation
- Test API integration
- Test step navigation
- Test error handling

---

## 17) Manual QA (copy-pasteable)
```bash
# Start development server
cd front
npm run dev

# Test onboarding flow
# 1. Navigate to /onboarding
# 2. Complete Step 1: Brand basics
# 3. Complete Step 2: Products
# 4. Complete Step 3: Delivery rates
# 5. Complete Step 4: Payments
# 6. Complete Integrations: WhatsApp
# 7. Verify all data is saved
```

---

## 18) Rollback Plan
- Remove onboarding components
- Remove onboarding hooks
- Remove onboarding pages
- Revert to basic auth flow

---

## Notes / Links
- PRD: `sayar_mvp_prd.md#merchant-onboarding`
- React Hook Form: https://react-hook-form.com/
- Zod: https://zod.dev/
- React Query: https://tanstack.com/query/latest
