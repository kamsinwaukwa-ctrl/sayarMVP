# Database Migrations

This directory contains database migration scripts for the Sayar WhatsApp Commerce Platform.

## Initial Setup

### 1. Configure Environment Variables

Update the `back/.env` file with your Supabase credentials:

```bash
# Edit the .env file in the back directory
cd back
nano .env  # or use your preferred editor
```

Replace the following values with your actual Supabase credentials:

```env
SUPABASE_URL=your_actual_supabase_project_url_here
SUPABASE_SERVICE_KEY=your_actual_supabase_service_role_key_here
```

### 2. Get Your Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to **Settings** > **API**
3. Copy:
   - **Project URL** → Use for `SUPABASE_URL`
   - **Service Role Key** → Use for `SUPABASE_SERVICE_KEY` (keep this secret!)

### 3. Install Dependencies

Make sure you have the backend dependencies installed:

```bash
cd back
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running Migrations

### Option 1: Using the Migration Script (Recommended)

Run the automated migration script:

```bash
cd back
python -m src.database.migrate
```

This will:
- Test the database connection
- Apply the complete schema migration
- Enable Row Level Security (RLS)
- Create all necessary indexes and constraints
- Verify the migration was successful

### Option 2: Manual SQL Execution

You can also run the SQL migration manually:

1. Open your Supabase dashboard
2. Go to **SQL Editor**
3. Copy the contents of `migrations/001_initial_schema.sql`
4. Paste and execute the SQL

### Option 3: Using psql Command Line

```bash
# Install psql if not already available
# On macOS: brew install postgresql
# On Ubuntu: sudo apt-get install postgresql-client

# Construct the connection string from your .env file
psql "postgresql://postgres:[service_key]@[host]:6543/postgres?sslmode=require" -f migrations/001_initial_schema.sql
```

## Migration Contents

The initial migration (`001_initial_schema.sql`) includes:

### Core Tables
- `merchants` - Tenant/merchant information
- `users` - User accounts with authentication
- `products` - Product catalog with inventory management
- `customers` - Customer profiles
- `orders` - Order management
- `payments` - Payment tracking

### Security Features
- **Row Level Security (RLS)** enabled on all tenant tables
- **UUID primary keys** for all tables
- **Database constraints** to prevent invalid data
- **JWT-based authentication** integration

### Business Logic
- **Money handling** in kobo (Nigerian currency subunit)
- **Inventory reservations** with TTL for checkout flows
- **Discount/coupon system** with various types
- **Outbox pattern** for reliable job processing
- **Webhook idempotency** tracking

## Verification

After running the migration, verify it was successful:

```sql
-- Check if tables were created
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Test a simple insert
INSERT INTO merchants (name, whatsapp_phone_e164, currency) 
VALUES ('Test Merchant', '+2341234567890', 'NGN');

SELECT * FROM merchants;
```

## Troubleshooting

### Common Issues

1. **Connection failed**
   - Verify your Supabase URL and Service Key
   - Check that your Supabase project is active

2. **Permission denied**
   - Ensure you're using the Service Role key, not the anonymous key
   - Check that your IP is allowed in Supabase network settings

3. **SSL connection error**
   - Supabase requires SSL connections
   - Make sure `sslmode=require` is included in connection string

4. **Migration already applied**
   - The migration is idempotent (can be run multiple times)
   - Existing objects won't be recreated

### Getting Help

If you encounter issues:

1. Check the Supabase documentation: https://supabase.com/docs
2. Verify your database credentials
3. Ensure your Supabase project has PostgreSQL extensions enabled
4. Check the migration script output for specific error messages

## Next Steps

After successful migration:

1. **Test the API**: Start the backend server and test endpoints
2. **Verify RLS**: Test that tenant isolation is working properly
3. **Seed data**: Add sample merchants, products, and users
4. **Frontend integration**: Connect the React frontend to the database

## Rollback

If you need to reset the database:

```sql
-- WARNING: This will delete all data!
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

Then re-run the migration script.