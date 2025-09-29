# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sayar is a WhatsApp-first commerce platform that enables SMEs (starting with beauty/cosmetics) to sell products directly through WhatsApp conversations. The platform features native WhatsApp catalog browsing, automated checkout flows, payment processing via Paystack/Korapay, and merchant dashboards.

## Architecture

- **Monorepo Structure**: Frontend (`/front`) and backend (`/back`) in separate directories
- **Event-Driven Architecture**: Database as single source of truth with broker pattern
- **Multi-tenant**: Each merchant is isolated via database-level security

### Frontend (`/front`)
- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: React Query for server state, React Context for client state
- **Authentication**: App-managed JWT (issued by backend)
- **Database**: Supabase (Postgres) with real-time subscriptions

### Backend (`/back`)
- **Framework**: FastAPI (Python)
- **Database**: Supabase Postgres with SQLAlchemy ORM
- **Job Processing**: Postgres outbox pattern + APScheduler worker
- **Architecture Pattern**: Service-oriented with Repository pattern
- **Testing**: pytest with integration tests using real database connections

## Common Commands

### Frontend Development
```bash
cd front
npm install          # Install dependencies
npm run dev          # Start development server (http://localhost:5173)
npm run build        # Build for production
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript checks
```

### Backend Development
```bash
cd back
python -m venv venv && source venv/bin/activate  # Create and activate virtual environment
pip install -r requirements.txt                  # Install dependencies

# Run development server (FastAPI)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Testing
pytest                        # Run all tests
pytest --cov=src             # Run tests with coverage
pytest tests/unit/           # Run unit tests only
pytest tests/integration/    # Run integration tests only

# Code quality
black .                      # Format code
mypy .                       # Type checking
pylint src/                  # Linting
```

### Full-Stack Development
1. Start ngrok for webhook testing: `ngrok http 8000`
2. Frontend terminal: `cd front && npm run dev`
3. Backend terminal: `cd back && source venv/bin/activate && uvicorn main:app --reload`

## Development Workflow

### Testing Philosophy
- **Integration First**: Test real FastAPI endpoints with actual database connections
- **Test Database**: Never mock Supabase services - use dedicated test database
- **Error Cases First**: Test failure scenarios before success paths
- **Full Verification**: Check both API responses and database state

### Backend Workflow
1. **Always start with tests** - Write integration tests that verify complete user flows
2. **Service/Repository Pattern** - All database operations through service classes
3. **Event-Driven Design** - Save to database, frontend subscribes to changes
4. **Postgres Outbox** - Use outbox pattern for reliable job processing
5. **Type Safety** - Use Pydantic models for all request/response validation

### Frontend Workflow
1. **Custom Hooks Over useEffect** - Prefer custom hooks for side effects and data fetching
2. **React Query** - Use for all server state management and API calls
3. **Component Organization** - Group by functionality (ui/, forms/, layout/, features/)
4. **Error Boundaries** - Always handle loading, error, and empty states
5. **TypeScript Strict** - Avoid 'any' type, use proper interfaces

## Key Architecture Principles

### Event-Driven Broker Architecture
- **Database as Truth**: Postgres (Supabase) is the single source of truth
- **No Direct Responses**: Backend saves to DB, frontend subscribes via React Query + Supabase Realtime
- **Decoupled Design**: Frontend and backend communicate through database state changes
- **Job Processing**: Use Postgres outbox + APScheduler for reliable async operations

### Multi-Tenant Security
- **Row Level Security (RLS)**: All tables use RLS policies with merchant_id isolation
- **JWT Claims**: Tokens include `merchant_id` and `role`; backend injects claims to DB session per request
- **Service Layer**: All database access goes through service classes that enforce tenant boundaries

### WhatsApp Commerce Integration
- **Meta Catalog Sync**: Products sync to Meta Commerce Catalog with stable retailer_id mappings
- **Webhook Processing**: Handle WhatsApp Cloud API webhooks with idempotency and signature verification
- **Inventory Management**: Atomic stock reservations with 15-minute TTL
- **Payment Processing**: Paystack/Korapay integration with webhook validation

## Important File Locations

### Configuration Files
- `front/package.json` - Frontend dependencies and scripts
- `back/requirements.txt` - Python dependencies
- `back/main.py` - FastAPI application entry point
- `front/vite.config.ts` - Vite build configuration
- `front/tailwind.config.js` - Tailwind CSS configuration

### Architecture Documentation
- `.cursor/rules/ADR.mdc` - Architecture Decision Records
- `back/.cursor/rules/backend-workflow.mdc` - Backend development guidelines
- `front/.cursor/rules/workflow.mdc` - Frontend development guidelines
- `READMEV1.md` - Comprehensive project documentation

### Database Schema
- Database models defined in `back/src/models/`
- Migrations managed via Supabase SQL editor
- Multi-tenant with RLS policies on all tables

## Common Patterns

### Backend API Endpoint
```python
@router.post("/api/v1/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    merchant: Merchant = Depends(get_current_merchant)
):
    # Use service classes for business logic
    service = OrderService(db)
    order = service.create_order(merchant.id, request)
    return OrderResponse.from_orm(order)
```

### Frontend Data Fetching
```tsx
// Custom hook with React Query
function useProducts(merchantId: string) {
  return useQuery({
    queryKey: ['products', merchantId],
    queryFn: () => api.getProducts(merchantId),
    enabled: !!merchantId,
  });
}

// Component usage with proper error handling
function ProductList() {
  const { data: products, isLoading, error } = useProducts(merchantId);
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!products?.length) return <EmptyState />;
  
  return <ProductGrid products={products} />;
}
```

### Service Class Pattern
```python
class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, merchant_id: UUID, order_data: CreateOrderRequest) -> Order:
        # Atomic operation with inventory reservation
        with self.db.begin():
            # Reserve inventory
            # Create order
            # Enqueue outbox jobs
        return order
```

## Environment Variables

### Frontend (`.env.local`)
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key  
VITE_API_BASE_URL=http://localhost:8000
```

### Backend (`.env`)
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
PAYSTACK_SECRET_KEY=your_paystack_secret_key
KORAPAY_SECRET_KEY=your_korapay_secret_key
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
JWT_SECRET_KEY=your_jwt_secret_key
```

## Testing Requirements

### Integration Testing
- All tests must use real database connections (no mocks for database operations)
- Test complete user workflows from API endpoint to database state
- Verify both response data and database records after each operation
- Use pytest fixtures for test data setup and cleanup

### Test Database Setup
- Tests require connection to Supabase test database
- Database transactions are rolled back after each test
- Use `pytest --cov=src` for coverage reporting

## Deployment

- **Backend**: Railway deployment with environment variables
- **Frontend**: Can be deployed to Vercel or Railway
- **Database**: Supabase hosted Postgres
- **Webhooks**: Use ngrok for local development, Railway for production

## Critical Considerations

### WhatsApp Integration
- All WhatsApp Cloud API calls must include proper error handling and retry logic
- Webhook signature verification is required for security
- Meta Catalog sync operations must be idempotent

### Payment Processing
- All payment amounts stored as integers in kobo (Nigerian currency)
- Payment webhook processing must be idempotent
- Always verify webhook signatures from payment providers

### Inventory Management
- Stock operations must be atomic to prevent overselling
- Use database-level constraints and transactions for inventory updates
- Implement reservation system with TTL for checkout flows

### Security
- Never commit API keys or secrets
- All multi-tenant data must be isolated via RLS policies
- JWT tokens must be validated on all protected endpoints
- Webhook signatures must be verified for all external integrations

## Authentication & Token Management

### JWT Token Lifecycle
- **Token Duration**: JWT tokens expire after 30 minutes (1800 seconds)
- **Token Claims**: Include `merchant_id`, `role`, `iat` (issued at), `exp` (expires at)
- **Authentication Flow**: Login → JWT → 30-min expiration → Need refresh

### Common Authentication Issues
```bash
# Decode JWT token to check expiration
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." | base64 -d

# Common 401 scenarios:
# 1. Token expired (most common after 30 minutes)
# 2. Invalid token format
# 3. Missing Authorization header
# 4. Backend JWT_SECRET_KEY mismatch
```

### Token Refresh Patterns
- **Frontend**: Should implement automatic token refresh on 401 responses
- **Manual Fix**: Refresh page or re-login when encountering 401 errors
- **API Client**: Should intercept 401s and attempt token refresh before failing

## Error Handling Patterns

### Cloudinary Integration Errors
```python
# Common Cloudinary issues:
# 1. Invalid transformation syntax: "c_limit,w_500" → use "w_500,h_500,c_limit"
# 2. Missing environment variables
# 3. Network timeouts
# 4. File size/format validation failures

# Debug Cloudinary uploads:
response = cloudinary.uploader.upload(
    file_content,
    folder=f"sayar/merchants/{merchant_id}/brand",
    public_id=image_uuid,
    overwrite=True,
    resource_type="image"
    # Note: Remove transformation parameter if causing errors
)
```

### Payment Provider Errors
- **Webhook Signature Verification**: Always verify signatures for security
- **Idempotency**: Payment operations must be idempotent
- **Provider Failover**: Implement fallback between Paystack and Korapay
- **Amount Format**: Store amounts as integers in kobo (Nigerian currency)

### Multi-Tenant RLS Errors
```sql
-- Common RLS issues:
-- 1. Missing merchant_id in queries
-- 2. Incorrect RLS policies
-- 3. Service-level tenant isolation bypassed

-- Debug RLS violations:
-- Check for "insufficient privilege" or "policy violation" errors
-- Verify merchant_id is properly set in database session
```

## Debugging & Troubleshooting

### Image Upload Issues
```bash
# Test image upload endpoint directly:
curl -X POST http://localhost:8000/api/v1/merchants/me/logo \
  -H "Authorization: Bearer [TOKEN]" \
  -F "file=@/path/to/image.png"

# Common issues:
# 1. JWT token expired (401 Unauthorized)
# 2. Invalid Cloudinary transformation syntax
# 3. File size exceeded (5MB limit)
# 4. Invalid file type (must be image/*)
```

### Authentication Debugging
```bash
# Get fresh authentication token:
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Test token validity:
curl -X GET http://localhost:8000/api/v1/merchants/me \
  -H "Authorization: Bearer [TOKEN]"
```

### Database Connection Issues
```bash
# Test database connectivity:
# 1. Verify SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
# 2. Check network connectivity to Supabase
# 3. Verify RLS policies are not blocking queries
# 4. Check merchant_id isolation in service classes
```

## Development Philosophy (from Cursor Rules)

### Backend Development Principles
- 🪟 **No broken windows**: Keep code clean from the start
- 🔄 **DRY**: Don't repeat yourself - refactor common patterns
- 🌐 **Leave it better**: Improve bad code as you encounter it
- 🧪 **Test First**: Write integration tests before implementation
- 👨‍💻 **SOLID**: Single purpose, self-contained functions

### Frontend UX Philosophy
- **Critical User Perspective**: Always adopt the view of a critical user
- **Self-Explanatory**: Users should never wonder "what's happening?"
- **Loading States**: Use spinners/skeletons for all async operations
- **Error States**: Show informative error messages via toast notifications
- **Empty States**: Display helpful empty state components
- **Mobile-First**: Use `100dvh` instead of `100vh` for mobile compatibility

## Testing Commands

### Running Specific Tests
```bash
# Run single test file:
pytest tests/integration/test_products.py

# Run specific test method:
pytest tests/integration/test_products.py::test_create_product

# Run tests with coverage for specific module:
pytest --cov=src/services tests/integration/

# Run tests matching pattern:
pytest -k "test_upload" tests/

# Run tests with verbose output:
pytest -v tests/integration/test_merchants.py
```

### Frontend Testing
```bash
# Run specific component tests:
npm test -- --testNamePattern="ImageUpload"

# Run tests in watch mode:
npm test -- --watch

# Run tests with coverage:
npm test -- --coverage
```

## API Debugging

### Common API Endpoints
```bash
# Authentication
POST /api/v1/auth/login
GET /api/v1/auth/me

# Merchant operations
GET /api/v1/merchants/me
PATCH /api/v1/merchants/me
POST /api/v1/merchants/me/logo

# Products
GET /api/v1/products
POST /api/v1/products
POST /api/v1/products/{id}/image

# Onboarding
GET /api/v1/merchants/me/onboarding
PUT /api/v1/merchants/me/onboarding
```

### Webhook Testing with ngrok
```bash
# Start ngrok tunnel:
ngrok http 8000

# Test webhook endpoints:
# - /api/v1/webhooks/whatsapp
# - /api/v1/webhooks/paystack
# - /api/v1/webhooks/korapay

# Verify webhook signatures in logs
```

### JWT Token Inspection
```javascript
// Decode JWT token in browser console:
function parseJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
}

// Usage: parseJwt("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
```

## Mobile Development Considerations

### Viewport and Layout
```css
/* Use mobile-safe viewport units */
.full-height {
  height: 100dvh; /* NOT 100vh */
}

/* Mobile-first responsive design */
.container {
  @apply px-4 sm:px-6 lg:px-8;
}
```

### Touch Interactions
- **Minimum touch targets**: 44px x 44px minimum for tap areas
- **Touch feedback**: Use hover states carefully (prefer focus states)
- **Scroll behavior**: Test overflow scrolling on mobile devices
- **WhatsApp Web compatibility**: Ensure components work within WhatsApp Web iframe

### Testing on Mobile
```bash
# Start dev server accessible on network:
npm run dev -- --host 0.0.0.0

# Test on mobile device:
# 1. Connect to same WiFi network
# 2. Visit http://[YOUR_IP]:5173
# 3. Test touch interactions and viewport behavior
```

When working on this codebase, always prioritize the integration testing approach, respect the event-driven architecture patterns, and ensure all multi-tenant security measures are properly implemented.

## Visual Development & Testing

### Design System

The project follows S-Tier SaaS design standards inspired by Stripe, Airbnb, and Linear. All UI development must adhere to:

- **Design Principles**: `/context/design-principles.md` - Comprehensive checklist for world-class UI
- **Component Library**: shadcn/ui with Tailwind configuration

### Quick Visual Check

**IMMEDIATELY after implementing any front-end change:**

1. **Identify what changed** - Review the modified components/pages
2. **Navigate to affected pages** - Use `mcp__playwright__browser_navigate` to visit each changed view
3. **Verify design compliance** - Compare against `/context/design-principles.md`
4. **Validate feature implementation** - Ensure the change fulfills the user's specific request
5. **Check acceptance criteria** - Review any provided context files or requirements
6. **Capture evidence** - Take full page screenshot at desktop viewport (1440px) of each changed view
7. **Check for errors** - Run `mcp__playwright__browser_console_messages` ⚠️

This verification ensures changes meet design standards and user requirements.

### Comprehensive Design Review

For significant UI changes or before merging PRs, use the design review agent:

```bash
# Option 1: Use the slash command
/design-review

# Option 2: Invoke the agent directly
@agent-design-review
```

The design review agent will:

- Test all interactive states and user flows
- Verify responsiveness (desktop/tablet/mobile)
- Check accessibility (WCAG 2.1 AA compliance)
- Validate visual polish and consistency
- Test edge cases and error states
- Provide categorized feedback (Blockers/High/Medium/Nitpicks)

### Playwright MCP Integration

#### Essential Commands for UI Testing

```javascript
// Navigation & Screenshots
mcp__playwright__browser_navigate(url); // Navigate to page
mcp__playwright__browser_take_screenshot(); // Capture visual evidence
mcp__playwright__browser_resize(
  width,
  height
); // Test responsiveness

// Interaction Testing
mcp__playwright__browser_click(element); // Test clicks
mcp__playwright__browser_type(
  element,
  text
); // Test input
mcp__playwright__browser_hover(element); // Test hover states

// Validation
mcp__playwright__browser_console_messages(); // Check for errors
mcp__playwright__browser_snapshot(); // Accessibility check
mcp__playwright__browser_wait_for(
  text / element
); // Ensure loading
```

### Design Compliance Checklist

When implementing UI features, verify:

- [ ] **Visual Hierarchy**: Clear focus flow, appropriate spacing
- [ ] **Consistency**: Uses design tokens, follows patterns
- [ ] **Responsiveness**: Works on mobile (375px), tablet (768px), desktop (1440px)
- [ ] **Accessibility**: Keyboard navigable, proper contrast, semantic HTML
- [ ] **Performance**: Fast load times, smooth animations (150-300ms)
- [ ] **Error Handling**: Clear error states, helpful messages
- [ ] **Polish**: Micro-interactions, loading states, empty states

## When to Use Automated Visual Testing

### Use Quick Visual Check for:

- Every front-end change, no matter how small
- After implementing new components or features
- When modifying existing UI elements
- After fixing visual bugs
- Before committing UI changes

### Use Comprehensive Design Review for:

- Major feature implementations
- Before creating pull requests with UI changes
- When refactoring component architecture
- After significant design system updates
- When accessibility compliance is critical

### Skip Visual Testing for:

- Backend-only changes (API, database)
- Configuration file updates
- Documentation changes
- Test file modifications
- Non-visual utility functions
 


## Sub agents
You have access to 5 sub agents:

	•	task-orchestrator-agent — TASK authoring & coordination
must be consulted for every new feature/brief that needs to become a Sayar TASK file. consumes .claude/tasks/context.md, task-local context, and PRD anchors. proposes exact scope, contracts, migrations/RLS, and cross-team touchpoints. delegates research only to sub-agents (UI, Payments, WhatsApp, Catalog), digests their outputs, and hands back a complete tasks/<TASK_ID>-<kebab-title>.mdc spec. after engineers implement, update context files (TOC, DIGEST, session notes) to maintain continuity.
	•	shadcn-ui-expert — UI design/pattern research
must be consulted for all UI build/tweak work. consumes the current .claude/tasks/context_session_x.md, proposes component structure, states, and accessibility notes; hands back a mini spec + snapshots before you implement. after you ship, update the session context.  ￼
	•	payments-integration — Paystack/Korapay verify & webhooks
must be consulted for payment provider setup, “verify connection” flows, webhook signature checks, idempotency, and failure modes. inputs: provider choice, keys (enc), envs; outputs: verify test plan, sample requests/responses, webhook schemas, retry/backoff matrix, and a pass/fail checklist aligned to PRD acceptance. scope includes metadata for reconciliation and link-generation patterns.  ￼
	•	whatsapp-integration — WhatsApp Cloud API, webhooks, template/flow wiring
must be consulted for WA message send, 24-hour window rules, webhook verification (X-Hub signature), auto-reply buttons, Flow-first + inline fallbacks, and order-event ingestion. inputs: WABA/phone number IDs, access token, app secret, webhook URL; outputs: endpoint map, test cURL set, error taxonomy, and end-to-end “hi → catalog → order event” validation script per PRD.  ￼
	•	catalog-integration — Meta Catalog (CSV/Graph)
must be consulted for product → catalog mapping, batch upserts, retailer_id strategy, image rules, and post-payment quantity sync. inputs: product schema, catalog id; outputs: items_batch payload templates, field-by-field validation rules, sync status taxonomy (pending/success/error), and visibility checklist (“product visible in Catalog”).  ￼


- Before you do any work, MUST view files in .claude/tasks/context_session_x.md file to get the full context (x being the id of the session we are operate, if file doesnt exist, then create one)
- context_session_x.md should contain most of context of what we did, overall plan, and sub agents will continuusly add context to the fileß
- After you finish the work, MUST update the .claude/tasks/context_session_x.md file to make sure others can get full context of what you did


## Examples
- Visual/UI work → `shadcn-ui-expert`
- Paystack/Korapay verify/webhooks → `payments-expert`
- WA Cloud (webhooks/templates/rate limits) → `wa-cloud-expert`
- Meta Catalog (CSV/Graph) → `meta-catalog-expert`

Sub agents will do research about the implementation, but you will do the actual implementation;
When passing task to sub agent, make sure you pass the context file, e.g. '.claude/tasks/session_context_x.md'.
After each sub agent finish the work, make sure you read the related documentation they created to get full context of the plan before you start executing

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.