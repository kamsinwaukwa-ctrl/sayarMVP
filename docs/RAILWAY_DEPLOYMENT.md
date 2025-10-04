# Railway Deployment Guide: Split Web + Worker Architecture

## Overview

Sayar uses a **split architecture** on Railway with two separate services:
- **Web Service**: FastAPI server handling HTTP requests (no background worker)
- **Worker Service**: Standalone APScheduler process handling outbox jobs (no HTTP server)

This architecture prevents deploy-time interruptions of background jobs and enables independent scaling.

## Architecture Benefits

✅ **Deploy Isolation**: Web deploys don't kill in-flight worker jobs
✅ **Independent Scaling**: Scale web horizontally (5x) while keeping 1-2 workers
✅ **Crash Isolation**: Web crash ≠ worker crash, and vice versa
✅ **Cost Efficiency**: Pay for what you need (5 web + 1 worker vs 5 web+worker combos)
✅ **Easier Debugging**: Separate logs for HTTP requests vs job processing

## How It Works

### Web Service (`railway.toml`)
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment**: `WORKER_ENABLED=false`
- **Purpose**: Handle HTTP API requests, webhooks, merchant dashboard
- **Scaling**: Horizontal (2-10 instances based on traffic)

### Worker Service (`railway.worker.toml`)
- **Start Command**: `cd back && python worker_entrypoint.py`
- **Environment**: `WORKER_ENABLED=true`
- **Purpose**: Process outbox jobs (WhatsApp messages, webhooks, catalog sync)
- **Scaling**: Vertical (1-2 instances max, leader election prevents duplicates)

### Leader Election

Both services use **Redis-based leader election**:
- Only ONE worker instance processes jobs at a time
- If leader crashes, another instance automatically takes over (~10s failover)
- Multiple web instances are fine (they don't process jobs)

## Railway Setup (Step-by-Step)

### 1. Create Web Service (Main API)

```bash
# In Railway dashboard:
1. Click "New Service"
2. Select your GitHub repo (sayarv1)
3. Name: "sayar-api"
4. Root Directory: /back
5. Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
6. Config File: railway.toml
```

**Environment Variables:**
```env
# Core
ENV=production
DEBUG=false
API_HOST=0.0.0.0
WORKER_ENABLED=false  # 🔴 IMPORTANT: Disable worker in web service

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...  # From Supabase dashboard

# WhatsApp
WHATSAPP_ACCESS_TOKEN=EAAx...
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_APP_SECRET=abc123...

# Payment Providers
PAYSTACK_SECRET_KEY=sk_live_...
KORAPAY_SECRET_KEY=sk_live_...

# Security
JWT_SECRET_KEY=your_super_secret_key_at_least_32_chars

# Redis (for leader election)
REDIS_URL=redis://:password@host:port  # From Railway Redis add-on

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789
CLOUDINARY_API_SECRET=abc123...
```

### 2. Create Worker Service (Background Jobs)

```bash
# In Railway dashboard:
1. Click "New Service" (in same project)
2. Select same GitHub repo (sayarv1)
3. Name: "sayar-worker"
4. Root Directory: /back
5. Start Command: cd back && python worker_entrypoint.py
6. Config File: railway.worker.toml
```

**Environment Variables:**
```env
# Core
ENV=production
DEBUG=false
WORKER_ENABLED=true  # 🟢 IMPORTANT: Enable worker in worker service
WORKER_MODE=standalone

# Database (same as web)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...

# WhatsApp (same as web)
WHATSAPP_ACCESS_TOKEN=EAAx...
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_APP_SECRET=abc123...

# Payment Providers (same as web)
PAYSTACK_SECRET_KEY=sk_live_...
KORAPAY_SECRET_KEY=sk_live_...

# Redis (same as web - for leader election)
REDIS_URL=redis://:password@host:port

# Cloudinary (same as web)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789
CLOUDINARY_API_SECRET=abc123...

# Worker-specific tuning (optional)
OUTBOX_WORKER_INTERVAL_SECONDS=30
RESERVATION_TTL_MINUTES=15
LOG_LEVEL=INFO
```

### 3. Add Redis Service (Leader Election)

```bash
# In Railway dashboard:
1. Click "New Service"
2. Select "Database" → "Redis"
3. Name: "sayar-redis"
4. Copy the REDIS_URL to both web and worker services
```

### 4. Configure Domain (Web Service Only)

```bash
# In sayar-api service settings:
1. Go to "Settings" → "Domains"
2. Add custom domain: api.usesayar.com
3. Configure DNS: CNAME → railway.app (follow Railway instructions)
```

## Verification Checklist

After deploying both services, verify:

### Web Service Logs
```
✅ "Application starting up"
✅ "Outbox worker disabled - running in web-only mode"
✅ "Started server process"
✅ "Uvicorn running on http://0.0.0.0:8000"
❌ Should NOT see "Starting outbox worker"
```

### Worker Service Logs
```
✅ "Starting standalone worker process"
✅ "Outbox worker started successfully"
✅ "Acquired leader lock" (one instance only)
✅ "Fetched jobs for processing"
❌ Should NOT see "Started server process" or "Uvicorn"
```

### Health Checks
```bash
# Web service (should respond with 200)
curl https://api.usesayar.com/healthz

# Worker service (no HTTP endpoint - check logs instead)
# Look for: "Leader heartbeat recorded" every 30 seconds
```

### Job Processing
```bash
# Test: Send WhatsApp message → check worker logs
# Expected flow:
# 1. Web receives webhook → saves to outbox_events table
# 2. Worker picks up job within 30 seconds
# 3. Worker logs: "Processing job", "Job completed successfully"
```

## Scaling Recommendations

### Web Service (API)
- **Minimum**: 2 instances (high availability)
- **Normal**: 3-5 instances (handles 1000+ req/min)
- **Peak**: 10 instances (Black Friday, big campaigns)
- **Autoscaling**: Based on CPU (target 70%) or request count

### Worker Service (Background Jobs)
- **Minimum**: 1 instance (sufficient for most workloads)
- **Recommended**: 2 instances (leader + hot standby)
- **Maximum**: 2 instances (leader election prevents >1 from working)
- **Autoscaling**: NOT recommended (leader election handles failover)

### Redis Service
- **Instance**: 1 (Railway manages HA automatically)
- **Memory**: 256MB (sufficient for leader locks + session data)

## Cost Estimates (Railway)

| Service | Instances | RAM/CPU | Monthly Cost |
|---------|-----------|---------|--------------|
| Web | 3 | 1GB / 1 vCPU | ~$15/instance = $45 |
| Worker | 1 | 512MB / 0.5 vCPU | ~$10/instance |
| Redis | 1 | 256MB | ~$5 |
| **Total** | | | **~$60/month** |

### Cost Comparison: Split vs Monolith
- **Monolith** (3 web+worker): 3 × $15 = $45 (but deploys kill jobs)
- **Split** (3 web + 1 worker): $45 + $10 = $55 (clean isolation)
- **Extra cost**: $10/month for job reliability ✅ Worth it

## Deployment Workflow

### Normal Deploy (Web Only)
```bash
# In Railway dashboard:
1. Push to main branch (auto-deploys web service)
2. Worker service stays running (no interruption)
3. In-flight jobs complete normally
4. New web version serves requests immediately
```

### Worker Deploy (Background Jobs)
```bash
# In Railway dashboard:
1. Deploy worker service separately
2. Old worker finishes current jobs (~30s max)
3. New worker takes over
4. Web service unaffected
```

### Rollback (If Issues)
```bash
# Web rollback:
1. Railway dashboard → sayar-api → Deployments
2. Click previous deploy → "Redeploy"
3. Worker continues processing (no impact)

# Worker rollback:
1. Railway dashboard → sayar-worker → Deployments
2. Click previous deploy → "Redeploy"
3. Short job pause (~10s) during switchover
```

## Troubleshooting

### Issue: Worker Not Processing Jobs

**Check:**
```bash
# 1. Verify worker is running
Railway dashboard → sayar-worker → Logs
Look for: "Worker process started successfully"

# 2. Check leader election
Look for: "Acquired leader lock"
If missing: Check REDIS_URL env var

# 3. Check for jobs
# Query Supabase:
SELECT COUNT(*) FROM outbox_events WHERE status = 'pending';
```

**Fix:**
```bash
# Restart worker service
Railway dashboard → sayar-worker → Settings → Restart
```

### Issue: Duplicate Job Processing

**Symptom**: Same job runs twice (duplicate WhatsApp messages)

**Cause**: Leader election not working (likely Redis issue)

**Fix:**
```bash
# 1. Check Redis connection
Railway dashboard → sayar-redis → Metrics (should show connections)

# 2. Verify REDIS_URL in both services
# Format: redis://:password@host:port

# 3. Restart worker service
```

### Issue: "Stuck in Processing" Jobs (Old Problem)

**Symptom**: Jobs status = 'processing' but never complete

**Cause**: Rare (should be fixed by split architecture)

**Fix:**
```bash
# 1. Check worker logs for errors
Railway dashboard → sayar-worker → Logs

# 2. Manually reset stuck jobs (if needed)
# Query Supabase:
UPDATE outbox_events
SET status = 'pending', next_run_at = NOW()
WHERE status = 'processing'
  AND updated_at < NOW() - INTERVAL '10 minutes';

# 3. Worker will retry jobs automatically
```

### Issue: High Worker CPU/Memory

**Check:**
```bash
Railway dashboard → sayar-worker → Metrics
Look for: CPU >80% sustained, Memory >90%
```

**Fix:**
```bash
# 1. Reduce batch size (process fewer jobs at once)
# Add env var: OUTBOX_WORKER_INTERVAL_SECONDS=60
# Add env var: OUTBOX_WORKER_BATCH_SIZE=10  # Default: 20

# 2. Scale worker instance up
Railway dashboard → sayar-worker → Settings → Resources
Increase RAM: 512MB → 1GB
```

## Local Development (Single Process)

For local dev, you can run web + worker in one process:

```bash
# In .env.local:
WORKER_ENABLED=true  # Enable worker locally

# Run:
cd back
uvicorn main:app --reload

# Both web server and worker will run in same process
# This is fine for dev, but DON'T do this in production!
```

## Migration Checklist (Existing Railway Setup → Split)

If you're migrating from a single-service setup:

- [ ] Create new worker service in Railway (step 2 above)
- [ ] Add REDIS_URL to both services (step 3 above)
- [ ] Update web service env: `WORKER_ENABLED=false`
- [ ] Update worker service env: `WORKER_ENABLED=true`
- [ ] Deploy web service (will stop embedded worker)
- [ ] Deploy worker service (takes over job processing)
- [ ] Verify logs (web logs "worker disabled", worker logs "worker started")
- [ ] Monitor metrics for 24h (ensure no stuck jobs)
- [ ] Delete old service (if you had separate one before)

## Further Reading

- [Railway Docs: Multi-Service Apps](https://docs.railway.app/guides/multi-service-apps)
- [APScheduler Leader Election](https://apscheduler.readthedocs.io/)
- [Postgres Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)

## Support

If you encounter issues:
1. Check Railway logs (both services)
2. Check Supabase logs (database queries)
3. Review this guide's troubleshooting section
4. Contact: [your support channel]
