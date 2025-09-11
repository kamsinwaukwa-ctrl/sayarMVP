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
- **Styling**: Tailwind CSS + Material-UI
- **State Management**: React Query for server state, React Context for client state
- **Authentication**: JWT with Supabase Auth
- **Database**: Supabase (Postgres) with real-time subscriptions

### Backend (`/back`)
- **Framework**: FastAPI (Python) - **Note: Currently uses Flask but migrating to FastAPI**
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

# Run development server
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
- **JWT Claims**: Authentication tokens contain merchant_id for access control
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
- `back/main.py` - FastAPI application entry point (currently Flask)
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

When working on this codebase, always prioritize the integration testing approach, respect the event-driven architecture patterns, and ensure all multi-tenant security measures are properly implemented.

## Visual Development & Testing

### Design System

The project follows S-Tier SaaS design standards inspired by Stripe, Airbnb, and Linear. All UI development must adhere to:

- **Design Principles**: `/context/design-principles.md` - Comprehensive checklist for world-class UI
- **Component Library**: NextUI with custom Tailwind configuration

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

## Additional Context

always use byterover-retrive-knowledge tool to get the related context before any tasks
always use byterover-store-knowledge to store all the critical informations after sucessful tasks
- Design review agent configuration: `/.claude/agents/design-review-agent.md`
- Design principles checklist: `/context/design-principles.md`
- Custom slash commands: `/context/design-review-slash-command.md`