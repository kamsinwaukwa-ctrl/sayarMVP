# Sayar WhatsApp Commerce Platform

**TL;DR:** A WhatsApp-first commerce platform that enables SMEs to sell products directly through WhatsApp conversations with native catalog browsing, automated checkout flows, payment processing, and merchant dashboards.

## Development Setup Checklist

### Prerequisites
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ and npm installed
- [ ] Git installed

### Backend Setup
- [ ] Clone repository: `git clone <repo-url>`
- [ ] Navigate to backend: `cd back`
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
- [ ] Install backend dependencies: `pip install -r requirements.txt`
- [ ] Run backend tests: `pytest`
- [ ] Start development server: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

### Frontend Setup
- [ ] Navigate to frontend: `cd front`
- [ ] Install frontend dependencies: `npm install`
- [ ] Run type checking: `npm run type-check`
- [ ] Start development server: `npm run dev`
- [ ] Run frontend build: `npm run build`

### Development Tools
- [ ] Set up pre-commit hooks: `pre-commit install`
- [ ] Verify linting passes: `pre-commit run --all-files`
- [ ] Verify CI pipeline works: Push changes and check GitHub Actions

## Architecture

### Tech Stack
- **Frontend:** React + Vite + TypeScript + Tailwind CSS + Material-UI
- **Backend:** FastAPI + Python + SQLAlchemy ORM
- **Database:** PostgreSQL + Supabase
- **Authentication:** JWT with Supabase Auth
- **Deployment:** Railway
- **Job Processing:** Postgres outbox pattern + APScheduler worker

### Directory Structure
```
sayarv1/
├── front/                    # React + Vite frontend
│   ├── src/
│   ├── public/
│   └── package.json
├── back/                     # FastAPI backend
│   ├── src/
│   ├── main.py
│   └── requirements.txt
├── migrations/               # Database migrations
├── tasks/                    # Task management files
├── .github/workflows/        # CI/CD pipelines
├── .pre-commit-config.yaml   # Pre-commit hooks
└── README.md
```

### Key Features
- **WhatsApp Integration:** Native catalog browsing and cart management
- **Event-Driven Architecture:** Database as single source of truth
- **Multi-Tenant Security:** Row Level Security (RLS) with merchant isolation
- **Payment Processing:** Paystack & Korapay integration
- **Inventory Management:** Atomic stock reservations with TTL
- **Observability:** Structured logging and metrics

## Development Workflow

### Backend Development
1. **Integration-First Testing:** Write tests that verify complete API flows
2. **Service/Repository Pattern:** All database operations through service classes
3. **Event-Driven Design:** Save to database, frontend subscribes to changes
4. **Type Safety:** Use Pydantic models for all request/response validation

### Frontend Development
1. **Custom Hooks:** Prefer custom hooks over useEffect for side effects
2. **React Query:** Use for all server state management and API calls
3. **Component Organization:** Group by functionality
4. **Error Boundaries:** Always handle loading, error, and empty states

### Code Quality
- **Formatting:** Black (Python), Prettier (TypeScript)
- **Linting:** Ruff (Python), ESLint (TypeScript)
- **Type Checking:** MyPy (Python), TypeScript compiler
- **Testing:** pytest (Python), Vitest (TypeScript)

## Common Commands

### Backend
```bash
# Development server
cd back && uvicorn main:app --reload

# Testing
cd back && pytest
cd back && pytest --cov=src

# Code quality
cd back && black .
cd back && ruff check .
cd back && mypy .
```

### Frontend
```bash
# Development server  
cd front && npm run dev

# Build and preview
cd front && npm run build
cd front && npm run preview

# Code quality
cd front && npm run lint
cd front && npm run type-check
```

### Full-Stack Development
1. Start backend: `cd back && uvicorn main:app --reload`
2. Start frontend: `cd front && npm run dev`
3. For webhook testing: Use ngrok to expose local backend

## Environment Variables

### Backend (.env)
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
PAYSTACK_SECRET_KEY=your_paystack_secret_key
KORAPAY_SECRET_KEY=your_korapay_secret_key
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
JWT_SECRET_KEY=your_jwt_secret_key
```

### Frontend (.env.local)
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=http://localhost:8000
```

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes following the development workflow
3. Ensure all tests pass: `npm test` (frontend) and `pytest` (backend)
4. Ensure pre-commit hooks pass: `pre-commit run --all-files`
5. Push to the feature branch and create a Pull Request
6. CI must pass before merging

## Deployment

- **Backend:** Railway with environment variables configured
- **Frontend:** Can be deployed to Vercel or Railway
- **Database:** Supabase hosted PostgreSQL
- **Webhooks:** Railway for production, ngrok for local development

## License

Private - All rights reserved