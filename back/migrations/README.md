# Meta Feeds Database Migrations

This directory contains database migrations for the Meta Commerce feed endpoint implementation.

## Deployment Sequence

**CRITICAL: Follow this exact order to avoid deployment issues**

### 1. Performance Indexes (First)
```bash
# Run in Supabase SQL editor or via your migration tool
psql -f meta_feeds_indexes.sql

# Or copy/paste contents into Supabase SQL editor
```
**File**: `meta_feeds_indexes.sql`
**Purpose**: Creates performance indexes for feed generation queries
**Safe to run**: Yes, uses `CREATE INDEX CONCURRENTLY`
**Estimated time**: 2-5 minutes depending on table size

### 2. RLS Bypass Function (Second)  
```bash
# Run in Supabase SQL editor with superuser privileges
psql -f meta_feeds_rls_function.sql

# IMPORTANT: May require superuser role for SECURITY DEFINER
```
**File**: `meta_feeds_rls_function.sql`  
**Purpose**: Creates SECURITY DEFINER function to safely bypass RLS
**Requires**: Superuser or function creator privileges
**Estimated time**: <1 minute

### 3. Application Code (Last)
```bash
# Deploy your application code after database changes
# The feed endpoints will be available immediately
```

## Validation Steps

After deployment, validate each step:

### Validate Indexes
```sql
-- Check that indexes were created
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE indexname LIKE 'idx_%feed%';

-- Should show 4 new indexes:
-- - idx_merchants_slug_feeds
-- - idx_products_feed_generation  
-- - idx_products_meta_sync_monitoring
-- - idx_products_merchant_updated
```

### Validate RLS Function
```sql
-- Test function exists and works
SELECT proname, proowner::regrole as owner, prosecdef as security_definer
FROM pg_proc 
WHERE proname = 'get_merchant_feed_data';

-- Test with a known merchant slug
SELECT * FROM get_merchant_feed_data('your-test-merchant-slug') LIMIT 5;

-- Should return merchant info + product data (or empty if no merchant)
```

### Validate Application Integration
```bash
# Test the feed endpoint
curl -v "http://localhost:8000/api/v1/meta/feeds/test-merchant/products.csv"

# Expected: 200 OK with CSV content or 404 if merchant not found
# Should include proper headers: Content-Type, ETag, Cache-Control
```

## Security Checklist

Before production deployment, verify:

- [ ] **Function Permissions**: `get_merchant_feed_data` owned by trusted role
- [ ] **Application Role**: App database role has EXECUTE permission on function  
- [ ] **Input Validation**: Function validates merchant_slug parameter
- [ ] **Query Restrictions**: Function only returns active, Meta-visible products
- [ ] **No Data Leakage**: Test with different merchant slugs to confirm isolation

## Performance Monitoring

After deployment, monitor performance:

```sql
-- Monitor function usage
SELECT schemaname, funcname, calls, total_time, mean_time 
FROM pg_stat_user_functions 
WHERE funcname = 'get_merchant_feed_data';

-- Monitor index effectiveness  
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE indexname LIKE 'idx_%feed%';

-- Check for slow queries (adjust threshold)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements 
WHERE query LIKE '%get_merchant_feed_data%' 
AND mean_exec_time > 100; -- milliseconds
```

## Rollback Instructions

**⚠️ DANGEROUS - Only use in emergencies**

### Remove Function (breaks feed endpoints)
```sql
-- This will break the feed API until function is restored
DROP FUNCTION IF EXISTS get_merchant_feed_data(TEXT);
```

### Remove Indexes (safe but impacts performance)
```sql
-- These can be safely removed, but will impact feed performance
DROP INDEX CONCURRENTLY IF EXISTS idx_merchants_slug_feeds;
DROP INDEX CONCURRENTLY IF EXISTS idx_products_feed_generation;
DROP INDEX CONCURRENTLY IF EXISTS idx_products_meta_sync_monitoring;  
DROP INDEX CONCURRENTLY IF EXISTS idx_products_merchant_updated;
```

## Troubleshooting

### Common Issues

**Function Permission Denied**
```
ERROR: permission denied for function get_merchant_feed_data
```
**Solution**: Grant EXECUTE permission to application role:
```sql
GRANT EXECUTE ON FUNCTION get_merchant_feed_data(TEXT) TO your_app_role;
```

**Function Returns No Data**
```sql
-- Debug: Check if merchant exists
SELECT id, name, slug FROM merchants WHERE slug = 'your-merchant-slug';

-- Debug: Check products for merchant
SELECT count(*) FROM products 
WHERE merchant_id = 'merchant-uuid' 
AND status = 'active' 
AND meta_catalog_visible = true;
```

**Slow Feed Generation**
- Check index usage with monitoring queries above
- Ensure `meta_feeds_indexes.sql` was deployed first
- Consider product count - feeds with >10k products may need optimization

## Support

For deployment issues:
1. Check Supabase logs for error details
2. Validate each step with the validation queries above  
3. Ensure proper role permissions for function creation
4. Test with a small merchant catalog first before production load