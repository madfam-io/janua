# Railway Deployment Guide

## Current Status: ✅ READY FOR RAILWAY DEPLOYMENT

All build issues have been resolved and the project is ready for Railway deployment.

## Deployment Steps

### 1. Connect to Railway

```bash
# Install Railway CLI if not already installed
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize the project
railway init
```

### 2. Environment Variables

Set the following environment variables in Railway:

```bash
# Required for all apps
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://plinto.railway.app

# For authentication (when backend is ready)
JWT_SECRET=your-secret-key-here
DATABASE_URL=postgresql://...

# For email service (when ready)
SENDGRID_API_KEY=your-sendgrid-key
```

### 3. Deploy

```bash
# Deploy to Railway
railway up

# Or connect GitHub repo for automatic deployments
railway link
```

## What's Deployed

Currently, Railway will deploy the **marketing site** as the primary application:
- URL: https://plinto.railway.app
- Health check: https://plinto.railway.app/health

## Build Configuration

The `config/railway.json` file is configured with:
- **Build Command**: `yarn install --frozen-lockfile && yarn build`
- **Start Command**: `yarn workspace @plinto/marketing start`
- **Health Check**: `/health` endpoint
- **Restart Policy**: ON_FAILURE with 3 retries

## Verified Working

✅ **Build**: All packages build successfully
✅ **TypeScript**: Core packages compile without errors
✅ **Dependencies**: All required dependencies installed
✅ **Health Check**: Endpoint configured and ready
✅ **Start Script**: Production start command configured

## Known Issues (Non-Blocking)

These issues exist but don't prevent deployment:
- Some test files have TypeScript errors (tests not run in production)
- Peer dependency warnings (handled by yarn workspaces)

## Post-Deployment Tasks

After successful Railway deployment:

1. **Add Custom Domain**
   ```bash
   railway domain
   ```

2. **Monitor Logs**
   ```bash
   railway logs
   ```

3. **Scale if Needed**
   ```bash
   railway scale
   ```

## Multiple Service Deployment

To deploy all services (admin, docs, demo, etc.), create separate Railway services:

```bash
# Create services for each app
railway service create admin
railway service create docs
railway service create demo
railway service create dashboard

# Configure each with appropriate start commands
# admin: yarn workspace @plinto/admin start
# docs: yarn workspace @plinto/docs start
# demo: yarn workspace @plinto/demo start
# dashboard: yarn workspace @plinto/dashboard start
```

## Troubleshooting

If deployment fails:

1. **Check logs**: `railway logs`
2. **Verify environment variables**: `railway variables`
3. **Test locally**: `yarn build && yarn start:prod`
4. **Check Railway status**: https://status.railway.app

## Support

For Railway-specific issues:
- Railway Discord: https://discord.gg/railway
- Railway Docs: https://docs.railway.app

---

**Status**: Ready for production deployment on Railway
**Last Verified**: 2025-09-09