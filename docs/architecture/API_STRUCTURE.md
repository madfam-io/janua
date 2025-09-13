# Plinto API Structure

## Current Architecture

The Plinto platform uses a **monorepo structure** with clear separation between frontend applications and the backend API:

### Directory Structure
```
plinto/
├── apps/
│   ├── api/          # ← Python FastAPI backend (deployed to Railway)
│   ├── admin/        # Next.js admin panel
│   ├── dashboard/    # Next.js user dashboard
│   ├── docs/         # Documentation site
│   └── marketing/    # Marketing website
├── packages/         # Shared SDKs and libraries
│   ├── js-sdk/       # JavaScript SDK
│   ├── react-sdk/    # React SDK
│   ├── go-sdk/       # Go SDK
│   └── ...           # Other SDKs
└── deployment/       # Infrastructure and deployment configs
```

## API Location

**The API is located at `/apps/api/`** - this is the single source of truth for the backend API.

### Why This Structure?

1. **Clear Separation**: Python backend in `/apps/api/`, TypeScript/JavaScript frontends in other `/apps/*` folders
2. **Independent Deployment**: Each app can be deployed independently
3. **Railway Compatibility**: The `/apps/api/` folder is configured for Railway deployment with:
   - `railway.json` - Railway configuration
   - `nixpacks.toml` - Build configuration
   - `requirements.txt` - Python dependencies
   - `Dockerfile` - Container configuration

## API Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis
- **Authentication**: JWT with refresh tokens
- **Rate Limiting**: Redis-backed token bucket algorithm
- **Deployment**: Railway (Production)

## Important Files

### Configuration
- `/apps/api/railway.json` - Railway deployment config
- `/apps/api/requirements.txt` - Python dependencies
- `/apps/api/.env.example` - Environment variables template

### Application Code
- `/apps/api/app/main.py` - FastAPI application entry point
- `/apps/api/app/config.py` - Application configuration
- `/apps/api/app/routers/` - API endpoints
- `/apps/api/app/models/` - Database models
- `/apps/api/app/services/` - Business logic
- `/apps/api/app/middleware/` - Middleware (auth, rate limiting, etc.)

## Deployment

The API is deployed to Railway from the `/apps/api/` directory:

```bash
# Railway looks for these files in /apps/api/:
- railway.json (deployment config)
- requirements.txt (dependencies)
- main.py (entry point)
```

## Development

To run the API locally:

```bash
cd apps/api
pip install -r requirements.txt
python main.py
```

Or with Docker:

```bash
cd apps/api
docker-compose up
```

## Migration Notes

- **Previously**: There was a duplicate `/api` folder at the root which has been removed
- **Currently**: All API code is consolidated in `/apps/api/`
- **No Changes Needed**: Railway deployment continues to work as before

## Why Not in Nx Workspace?

While the frontend apps use Nx workspace tooling, the Python API is kept separate because:

1. **Different ecosystem**: Python vs JavaScript/TypeScript
2. **Different build tools**: pip/Poetry vs npm/yarn
3. **Different deployment**: Railway (Python) vs Vercel/Netlify (Next.js)
4. **Independence**: API can be developed and deployed independently

This structure provides the best of both worlds - a unified monorepo for code organization while maintaining ecosystem-appropriate tooling for each component.