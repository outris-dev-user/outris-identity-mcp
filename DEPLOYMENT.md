# Deployment Guide - Outris Identity MCP Server

This guide covers deploying Outris Identity MCP with all three transports (Streamable HTTP, SSE, STDIO).

---

## Table of Contents

1. [Railway Deployment (Current)](#railway-deployment)
2. [Changing Deployment Source](#changing-deployment-source)
3. [Environment Configuration](#environment-configuration)
4. [Health Checks & Monitoring](#health-checks--monitoring)
5. [Switching from number-lookup to outris-identity-mcp](#switching-from-number-lookup)

---

## Railway Deployment

### Current Setup

Your MCP server is deployed on Railway at:
- **URL**: `https://mcp-server.outris.com`
- **Transports**:
  - `POST /http` - Streamable HTTP (new, primary)
  - `GET /sse` - SSE (legacy, backward compat)
  - Health: `GET /health`
  - Tools list: `GET /tools`

### Deployment Architecture

```
GitHub (outris-identity-mcp)
    ↓
    Push to main/deploy branch
    ↓
Railway (CI/CD)
    ↓
    Builds: docker build .
    Runs: docker run with Dockerfile CMD
    ↓
    Entrypoint: python -m mcp_server --http
    ↓
Exposes: https://mcp-server.outris.com
```

### How to Deploy

**Option 1: Automatic (Recommended)**

Railway automatically deploys when you push to the designated branch (usually `main` or `deploy`).

```bash
# Make your changes
git add .
git commit -m "Add Streamable HTTP support"

# Push to trigger Railway deployment
git push origin main  # or your deploy branch

# Check Railway dashboard for deployment status
# https://railway.app/project/...
```

**Option 2: Manual Redeploy**

Via Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up

# Redeploy latest
railway redeploy
```

---

## Changing Deployment Source

### ⚠️ IMPORTANT: Switching from number-lookup to outris-identity-mcp

Currently:
- **`number-lookup/mcp-server/`** is deployed (old)
- **`outris-identity-mcp/`** is just documentation (not deployed)

To switch:

### Step 1: Update Railway Project Settings

1. Go to [Railway Dashboard](https://railway.app)
2. Select your project
3. Go to **Settings** > **Source**
4. Change **Root Directory** from:
   - `number-lookup/mcp-server/` → `outris-identity-mcp/`

OR (if using separate Railway projects):

1. Create new Railway project for `outris-identity-mcp`
2. Link to your GitHub repo
3. Set **Root Directory** to `outris-identity-mcp/`
4. Update DNS/custom domain to point to new project

### Step 2: Update Environment Variables

Ensure these are set in Railway **Environment** tab:

```bash
# API & Auth
OUTRIS_API_KEY=your_api_key_here  # Get from https://portal.outris.com

# Database
DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Server
LOG_LEVEL=INFO

# Features
ENABLE_KYC_TOOLS=true
```

### Step 3: Test Before Switching DNS

```bash
# Get temporary Railway URL for new deployment
# From Railway dashboard: https://outris-identity-mcp-abc123.railway.app

# Test Streamable HTTP endpoint
curl https://outris-identity-mcp-abc123.railway.app/health

# Test tools listing
curl https://outris-identity-mcp-abc123.railway.app/tools

# Test execution
curl -X POST https://outris-identity-mcp-abc123.railway.app/http \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Step 4: Update DNS (if needed)

If using custom domain `mcp-server.outris.com`:

1. Update DNS `CNAME` to point to new Railway domain
2. Enable Railway custom domain in project settings
3. SSL certificate auto-generated

### Step 5: Archive Old Deployment

Once everything is working:

```bash
# Keep number-lookup for historical reference
git tag release/mcp-server-v1-sse  # Tag final SSE-only version
git archive release/mcp-server-v1-sse -o archive/number-lookup-mcp-final.tar.gz

# Or just keep in repo under /archive/
```

---

## Environment Configuration

### Required Environment Variables

**`OUTRIS_API_KEY`**
- Default API key for demo/public access
- Example: `mcp_oObmRx4pFya_vGxX3oHHCXP1d02DXzQn`
- Can be empty if all requests provide Authorization header

**`DATABASE_URL`** (Required)
- PostgreSQL connection string
- Example: `postgresql://user:pass@neon.tech/dbname?sslmode=require`
- Must support SSL (Neon requirement)

**`LOG_LEVEL`**
- Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- Default: `INFO`

**`ENABLE_KYC_TOOLS`**
- Enable/disable KYC verification tools
- Options: `true`, `false`
- Default: `true`

### Optional Environment Variables

```bash
# Server binding (rarely needed - Railway sets defaults)
HOST=0.0.0.0
PORT=8000

# CORS configuration
CORS_ORIGINS=*
CORS_CREDENTIALS=true

# API rate limiting
DEFAULT_RATE_LIMIT_PER_MINUTE=100
DEFAULT_RATE_LIMIT_PER_DAY=10000

# Logging
LOG_FORMAT=json  # or 'plain'
LOG_DIR=/var/log/mcp
```

### Setting in Railway

1. Go to Railway Project > **Environment**
2. Add variables directly or upload `.env` file
3. Click **Deploy** to apply changes

---

## Health Checks & Monitoring

### Automated Health Checks

Railway automatically performs HTTP health checks:

- **Endpoint**: `GET /health`
- **Interval**: Every 10 seconds
- **Timeout**: 5 seconds
- **Unhealthy Threshold**: 3 consecutive failures

Configure in Railway project settings if needed.

### Manual Health Verification

```bash
# Check if server is healthy
curl https://mcp-server.outris.com/health

# Response:
# {
#   "status": "healthy",
#   "server": "outris-mcp-server",
#   "version": "2.0.0",
#   "transport": "streamable-http+sse",
#   "tools_count": 8
# }
```

### Monitoring Endpoints

**Server Info**
```bash
curl https://mcp-server.outris.com/
```

**Tools Discovery**
```bash
curl https://mcp-server.outris.com/tools
```

**Real Tool Execution** (requires auth)
```bash
curl -X POST https://mcp-server.outris.com/http \
  -H "Authorization: Bearer YOUR_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### Logs Monitoring

Via Railway CLI:

```bash
# Follow logs in real-time
railway logs --follow

# View last 100 lines
railway logs --tail 100

# Search for errors
railway logs | grep ERROR
```

Via Railway Dashboard:

1. Go to project > **Deployments**
2. Click latest deployment
3. View **Logs** tab

---

## Scaling & Performance

### Railway Deployment Plan

As of v2.0, deployments are configured with:

- **Plan**: Pro or higher (required for PostgreSQL SSL)
- **Instances**: 1 (auto-scales to 2+ with custom config)
- **Memory**: 512MB (sufficient for MCP server)
- **CPU**: Shared

### Scaling Configuration

To enable auto-scaling with Railway:

1. Go to **Settings** > **Plan**
2. Upgrade to **Standard** or higher
3. Enable **Auto-scaling** under compute
4. Set min/max instances

### Performance Optimization

**Streamable HTTP** is optimized for:
- ✅ High concurrency (stateless)
- ✅ Easy load balancing
- ✅ Horizontal scaling
- ✅ No connection affinity needed

**SSE** limitations:
- ❌ Requires sticky sessions for scaling
- ❌ Connection overhead
- Keep for backward compat only

---

## Troubleshooting Deployments

### Issue: Deployment Fails

**Check Railway Logs**:
```bash
railway logs | grep ERROR
```

**Common causes**:
1. Missing environment variables
2. Database connection failed
3. Invalid Python dependencies

**Fix**:
```bash
# Ensure all env vars are set
railway up  # Force redeploy

# Check logs for specific error
railway logs --tail 50
```

### Issue: 502 Bad Gateway

**Causes**:
1. Server crashed
2. Port not listening
3. Health check failing

**Fix**:
```bash
# Check if server is running
curl https://mcp-server.outris.com/health

# View error logs
railway logs | grep -i "error\|exception"

# Check Dockerfile CMD
cat Dockerfile  # Should have correct entrypoint
```

### Issue: Slow Performance

**Check transport**:
- If using SSE with many concurrent requests → Switch to HTTP
- HTTP (Streamable) performs better under load

**Check database**:
```sql
-- In Neon dashboard
SELECT count(*) FROM pg_stat_statements 
WHERE query LIKE '%leak_osint%'
```

### Issue: API Key Authentication Fails

**Check header format**:
```bash
# Correct:
-H "Authorization: Bearer YOUR_KEY"

# Wrong:
-H "Authorization: YOUR_KEY"
-H "X-API-Key: YOUR_KEY"
```

---

## Rollback Procedure

If new version causes issues:

### Quick Rollback

```bash
# Via Railway CLI
railway rollback <previous-deployment-id>

# Or in dashboard: Deployments > Previous > Rollback
```

### Version Pinning

To pin specific version:

1. Go to **Settings** > **Source**
2. Set **Branch** to specific git tag (e.g., `v2.0.0`)
3. Redeploy

---

## Maintenance Tasks

### Weekly

```bash
# Check logs for errors
railway logs | grep ERROR

# Verify health check passing
curl -s https://mcp-server.outris.com/health | jq .
```

### Monthly

```bash
# Review deployment metrics
# Go to Railway dashboard > Metrics

# Check database performance
# In Neon dashboard > Insights

# Update dependencies
pip install --upgrade -r requirements.txt
git commit -am "Update dependencies"
git push  # Triggers redeploy
```

### Quarterly

```bash
# Test all endpoints
./test_server.sh

# Load test
ab -n 1000 -c 10 https://mcp-server.outris.com/tools

# Update documentation
# Review SETUP.md, ARCHITECTURE.md, etc.
```

---

## Registry Deployment Checklist

Before submitting to official MCP registry:

- [ ] Dockerfile is correct and tested
- [ ] All 3 transports working (HTTP, SSE, STDIO)
- [ ] Health check responds ✅
- [ ] Tools list endpoint works
- [ ] Tool execution (with auth) works
- [ ] Documentation complete (README, SETUP, ARCHITECTURE)
- [ ] LICENSE file present (MIT)
- [ ] GitHub repo is public
- [ ] `mcp.json` registry config ready
- [ ] All environment variables documented
- [ ] Error handling tested
- [ ] Rate limiting working
- [ ] Database connection pooling confirmed

---

## Support

- Railway support: https://railway.app/support
- GitHub issues: https://github.com/outris/outris-identity-mcp/issues
- Outris support: support@outris.com
