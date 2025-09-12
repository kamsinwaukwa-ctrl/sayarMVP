# Manual Deployment Setup Guide
## Sayar Production Deployment with usesayar.com

> **Target Architecture:**  
> - **Landing**: `https://usesayar.com` (existing)
> - **Web App**: `https://usesayar.com/app` (new - Vercel)
> - **API**: `https://api.usesayar.com` (new - Railway)
> - **Webhooks**: `https://api.usesayar.com/api/v1/webhooks/whatsapp` ✅

---

## Step 1: Create Required Accounts

### **Railway Account Setup**
1. **Go to**: [railway.app](https://railway.app)
2. **Sign up** with GitHub account (recommended)
3. **Create new project** from GitHub repository
4. **Select repository**: `your-username/sayarv1`
5. **Select service**: Choose `back/` directory
6. **Plan**: Start with Hobby plan ($5/month)

### **Vercel Account Setup**
1. **Go to**: [vercel.com](https://vercel.com)
2. **Sign up** with GitHub account (recommended)
3. **Import project** from GitHub repository
4. **Select repository**: `your-username/sayarv1`
5. **Framework preset**: Detect automatically (Vite)
6. **Root directory**: `front/`
7. **Plan**: Free tier (sufficient for start)

---

## Step 2: Information You Need to Gather

### **🔑 Required Information Checklist**

#### **From Supabase (you already have these)**
- [ ] **Supabase URL**: `https://jdtktyvoxsnpiuirwpmr.supabase.co`
- [ ] **Supabase Service Key**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- [ ] **Supabase Anon Key**: (for frontend)
- [ ] **Database URL**: (full PostgreSQL connection string)

#### **From WhatsApp Cloud API**
- [ ] **WhatsApp Access Token**: `your_whatsapp_access_token`
- [ ] **Phone Number ID**: `your_whatsapp_phone_number_id`
- [ ] **Business Account ID**: `your_whatsapp_business_account_id`
- [ ] **Webhook Verify Token**: `your_webhook_verify_token`

#### **From Meta Business (for Catalog)**
- [ ] **Meta App ID**: `your_meta_app_id`
- [ ] **Meta App Secret**: `your_meta_app_secret`
- [ ] **System User Token**: `your_meta_system_user_token`

#### **From Payment Providers**
- [ ] **Paystack Secret Key**: `your_paystack_secret_key`
- [ ] **Paystack Public Key**: `your_paystack_public_key`
- [ ] **Korapay Secret Key**: `your_korapay_secret_key`
- [ ] **Korapay Public Key**: `your_korapay_public_key`

#### **Generate New (Production Only)**
- [ ] **JWT Secret Key**: Generate strong 32+ character key
- [ ] **Webhook Verify Token**: Generate random string for Meta webhook verification

---

## Step 3: Domain Configuration

### **DNS Settings for usesayar.com**
You'll need to add these DNS records:

```
Type: CNAME
Name: api
Value: [Railway will provide this]
TTL: 300

Type: A (or CNAME)
Name: @ (root domain)
Value: [Vercel will provide this for /app routing]
TTL: 300
```

### **Domain Setup Process**
1. **Railway**: Add custom domain `api.usesayar.com` in project settings
2. **Vercel**: Configure domain routing for `usesayar.com/app`
3. **DNS**: Update your domain provider with provided values

---

## Step 4: Environment Variables Setup

### **Backend (Railway) Environment Variables**

**In Railway dashboard → Your Project → Variables:**

```env
# Application
ENV=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# Database (Your Supabase)
SUPABASE_URL=https://jdtktyvoxsnpiuirwpmr.supabase.co
SUPABASE_SERVICE_KEY=[PASTE YOUR SUPABASE SERVICE KEY HERE]
DATABASE_URL=[PASTE YOUR FULL DATABASE URL HERE]

# Session Pooler (if using)
DB_USER=postgres.jdtktyvoxsnpiuirwpmr
DB_PASSWORD=[PASTE YOUR DB PASSWORD HERE]
DB_HOST=aws-1-eu-west-3.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres

# Authentication (GENERATE NEW FOR PRODUCTION)
JWT_SECRET_KEY=[GENERATE STRONG 32+ CHARACTER STRING]
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# WhatsApp Cloud API
WHATSAPP_ACCESS_TOKEN=[PASTE YOUR WHATSAPP TOKEN HERE]
WHATSAPP_PHONE_NUMBER_ID=[PASTE YOUR PHONE NUMBER ID HERE]
WHATSAPP_BUSINESS_ACCOUNT_ID=[PASTE YOUR BUSINESS ACCOUNT ID HERE]
WHATSAPP_WEBHOOK_VERIFY_TOKEN=[GENERATE RANDOM STRING FOR WEBHOOK VERIFICATION]

# Payment Providers
PAYSTACK_SECRET_KEY=[PASTE YOUR PAYSTACK SECRET KEY HERE]
PAYSTACK_PUBLIC_KEY=[PASTE YOUR PAYSTACK PUBLIC KEY HERE]
KORAPAY_SECRET_KEY=[PASTE YOUR KORAPAY SECRET KEY HERE]
KORAPAY_PUBLIC_KEY=[PASTE YOUR KORAPAY PUBLIC KEY HERE]

# Meta Business (for Catalog API)
META_APP_ID=[PASTE YOUR META APP ID HERE]
META_APP_SECRET=[PASTE YOUR META APP SECRET HERE]
META_SYSTEM_USER_TOKEN=[PASTE YOUR META SYSTEM USER TOKEN HERE]

# URLs (Custom Domains)
FRONTEND_URL=https://usesayar.com/app
WEBHOOK_BASE_URL=https://api.usesayar.com
CORS_ORIGINS=https://usesayar.com

# Logging & Processing
LOG_LEVEL=INFO
OUTBOX_WORKER_INTERVAL_SECONDS=30
RESERVATION_TTL_MINUTES=15
RATE_LIMIT_PER_MERCHANT_PER_MINUTE=60
WORKER_ENABLED=true
```

### **Frontend (Vercel) Environment Variables**

**In Vercel dashboard → Your Project → Settings → Environment Variables:**

```env
# API Configuration
VITE_API_BASE_URL=https://api.usesayar.com

# Supabase (Client)
VITE_SUPABASE_URL=https://jdtktyvoxsnpiuirwpmr.supabase.co
VITE_SUPABASE_ANON_KEY=[PASTE YOUR SUPABASE ANON KEY HERE]

# Environment
VITE_ENV=production
```

---

## Step 5: GitHub Actions Secrets

### **In GitHub Repository → Settings → Secrets and Variables → Actions:**

**Add these Repository Secrets:**

```
# Railway
RAILWAY_TOKEN=[Get from Railway → Account Settings → API Keys]
RAILWAY_SERVICE_ID=[Get from Railway → Project → Service ID]

# Vercel
VERCEL_TOKEN=[Get from Vercel → Account Settings → API Keys]
VERCEL_ORG_ID=[Get from Vercel → Account Settings → Team ID]
VERCEL_PROJECT_ID=[Get from Vercel → Project → Settings → General]

# Supabase (for frontend build)
VITE_SUPABASE_URL=https://jdtktyvoxsnpiuirwpmr.supabase.co
VITE_SUPABASE_ANON_KEY=[PASTE YOUR SUPABASE ANON KEY HERE]
```

---

## Step 6: WhatsApp Webhook Configuration

### **✅ Webhook URL Setup**
Your WhatsApp webhook URL will be:
```
https://api.usesayar.com/api/v1/webhooks/whatsapp
```

### **Meta Developer Console Setup**
1. **Go to**: [developers.facebook.com](https://developers.facebook.com)
2. **Select your app** → WhatsApp → Configuration
3. **Webhook URL**: `https://api.usesayar.com/api/v1/webhooks/whatsapp`
4. **Verify Token**: Use the `WHATSAPP_WEBHOOK_VERIFY_TOKEN` you generated
5. **Subscribe to**: `messages`, `message_status`, `message_deliveries`

### **Webhook Features**
- **Auto-scaling**: Railway handles traffic spikes
- **HTTPS**: Required by WhatsApp, automatically provided
- **Reliability**: Built-in health checks and restart policies
- **Monitoring**: Railway provides request logs and metrics

---

## Step 7: Payment Webhook Configuration

### **Paystack Webhooks**
- **URL**: `https://api.usesayar.com/api/v1/webhooks/paystack`
- **Events**: `charge.success`, `charge.failed`

### **Korapay Webhooks**
- **URL**: `https://api.usesayar.com/api/v1/webhooks/korapay`
- **Events**: Payment confirmation events

---

## Step 8: Deployment Process

### **Initial Deployment**
1. **Push to main branch**: All configuration files are ready
2. **GitHub Actions will**:
   - Run tests (backend + frontend)
   - Deploy backend to Railway
   - Deploy frontend to Vercel
   - Verify health checks

### **Verify Deployment**
- **API Health**: `https://api.usesayar.com/healthz`
- **API Docs**: `https://api.usesayar.com/docs`
- **Frontend**: `https://usesayar.com/app`
- **Landing**: `https://usesayar.com` (existing - should still work)

---

## Step 9: Post-Deployment Checklist

### **Functional Testing**
- [ ] **Health checks pass**: API returns 200 OK
- [ ] **Frontend loads**: Dashboard accessible at `/app`
- [ ] **Authentication works**: Sign up/login flow
- [ ] **Database connectivity**: Can create/read data
- [ ] **CORS configured**: Frontend can call API

### **Integration Testing**
- [ ] **WhatsApp webhooks**: Test webhook endpoint receives calls
- [ ] **Payment webhooks**: Test payment provider webhook delivery
- [ ] **Meta Catalog**: Test product sync (if BE-010 implemented)
- [ ] **CSV feeds**: Test feed URLs (if BE-010.1 implemented)

### **Monitoring Setup**
- [ ] **Railway metrics**: CPU, memory, requests visible
- [ ] **Vercel analytics**: Page views and performance data
- [ ] **Error tracking**: Check application logs for errors
- [ ] **Uptime monitoring**: Services responding consistently

---

## Step 10: Troubleshooting Common Issues

### **Backend Deployment Issues**
```bash
# Check Railway logs
railway logs --tail

# Check environment variables
railway variables

# Restart service
railway restart
```

### **Frontend Deployment Issues**
```bash
# Check Vercel logs in dashboard
# Verify environment variables in Vercel dashboard
# Check custom domain configuration
```

### **Domain Issues**
```bash
# Check DNS propagation
dig api.usesayar.com
nslookup usesayar.com

# Verify SSL certificates
curl -I https://api.usesayar.com
```

### **Webhook Issues**
```bash
# Test webhook endpoints
curl -X POST https://api.usesayar.com/api/v1/webhooks/whatsapp

# Check webhook logs in Railway dashboard
# Verify webhook verification token matches Meta configuration
```

---

## Step 11: Security Verification

### **Security Checklist**
- [ ] **HTTPS enforced**: All endpoints use SSL
- [ ] **Environment variables**: Stored securely in platform dashboards
- [ ] **JWT secrets**: Strong production keys generated
- [ ] **CORS configured**: Only allow frontend domain
- [ ] **Database security**: RLS policies enabled
- [ ] **Webhook signatures**: Verify incoming webhook authenticity

---

## Step 12: Cost Monitoring

### **Expected Monthly Costs**
- **Railway Hobby**: $5/month
- **Vercel Free**: $0/month (within limits)
- **Domain costs**: $0 (using existing usesayar.com)
- **Total**: **$5/month** = **$15 over 3 months**

### **Usage Monitoring**
- **Railway**: Monitor CPU/memory in dashboard
- **Vercel**: Monitor bandwidth/function usage
- **Set alerts**: Both platforms provide usage alerts

---

## Need Help?

### **Platform Support**
- **Railway**: [railway.app/help](https://railway.app/help)
- **Vercel**: [vercel.com/support](https://vercel.com/support)
- **GitHub Actions**: Check logs in repository Actions tab

### **Platform Documentation**
- **Railway**: [docs.railway.app](https://docs.railway.app)
- **Vercel**: [vercel.com/docs](https://vercel.com/docs)

---

## Summary

This setup gives you:
- ✅ **Professional domains**: `api.usesayar.com` + `usesayar.com/app`
- ✅ **WhatsApp webhook ready**: Stable HTTPS endpoint for Meta
- ✅ **Payment webhooks ready**: Endpoints for Paystack/Korapay
- ✅ **Auto-scaling**: Handle traffic spikes automatically  
- ✅ **CI/CD pipeline**: Automated testing and deployment
- ✅ **Cost-effective**: $5/month total for production hosting
- ✅ **Enterprise-ready**: SSL, monitoring, health checks included

Your existing landing page at `usesayar.com` will continue working while the new app runs at `usesayar.com/app`!