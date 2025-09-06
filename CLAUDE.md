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