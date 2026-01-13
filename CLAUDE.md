# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

iPoor is a Management Information System (MIS) for Poverty Reduction in Vietnam. It consists of a FastAPI backend with MySQL database and a static HTML/JS frontend served via nginx.

## Development Commands

### Docker (Recommended)

```bash
# Start all services
docker compose up -d --build

# Rebuild specific service after changes
docker compose up -d --build api  # Backend
docker compose up -d --build fe   # Frontend

# View logs
docker compose logs -f api

# Reset database (destroys all data)
docker compose down && docker volume rm ipoor_ipoor_db_data && docker compose up -d --build
```

### Backend (Local Development)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head                                  # Apply migrations
alembic revision --autogenerate -m "describe change"  # Generate new migration

# Seed data
python -m app.seeds.seed_all           # All seed data
python -m app.seeds.sample_households  # Households only
python -m app.seeds.sample_policies    # Policies only
```

### Seed Data in Docker

```bash
docker exec -it ipoor_api sh -c "cd /app && python -m app.seeds.seed_all"
```

## Architecture

### Monorepo Structure

```
iPoor/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── FE/               # Static HTML/JS + nginx
└── docker-compose.yml
```

### Backend (`backend/`)

- **Framework**: FastAPI with Pydantic schemas
- **ORM**: SQLAlchemy 2.0 with MySQL (PyMySQL driver)
- **Auth**: JWT tokens via python-jose, bcrypt password hashing
- **Migrations**: Alembic

Key directories:
- `app/routers/` - API endpoints (auth, households, policies, data_collections, gis, dashboard, etc.)
- `app/models/` - SQLAlchemy ORM models (User, Household, Policy, DataCollection, ActivityLog, PolicyDraft)
- `app/schemas/` - Pydantic request/response schemas
- `app/constants.py` - Enums (Roles, PovertyStatus, CollectionStatus, PolicyCategory)
- `app/deps.py` - FastAPI dependencies (get_db, get_current_user, authenticate_user)
- `app/seeds/` - Demo data seeders

### Frontend (`FE/`)

- **Type**: Static HTML pages with vanilla JavaScript
- **Server**: nginx (serves files and proxies `/api/` to backend)
- **Config**: `FE/config.js` auto-detects API base URL

Page structure:
- `Auth/` - Login.html, Signup.html, ForgotPassword.html
- `HomePage/` - Dashboard and authenticated features (HomePage.html, HouseholdList.html, PolicyList.html, GISMap.html, etc.)
- `LandingPage/` - Public pages (index.html, NewsPublic.html, GISPublic.html)

### GIS Data

Backend reads GIS data from `FE/data/processed/`:
- `gis_indicator_values.csv` - Indicator data by region
- `region_map.json` - Geographic region definitions

**Important**: Backend Dockerfile uses repo root as build context to access these files. Always build from repo root:
```bash
docker build -f backend/Dockerfile -t ipoor-api .  # Correct
# NOT: cd backend && docker build ...
```

## Key Patterns

### Authentication

- JWT stored in localStorage (`ipoor_access_token`) or sessionStorage
- Token sent via `Authorization: Bearer <token>` header
- Role-based access: `admin`, `province_officer`, `district_officer`, `commune_officer`

### Environment Variables

Backend requires `.env` file (copy from `.env.example`):
- `DB_HOST=db` when using docker-compose, `127.0.0.1` for local MySQL
- `ALLOWED_ORIGINS` - CORS whitelist (comma-separated)
- `JWT_SECRET` - Must be strong in production

### API Base URL

Frontend uses `window.IPOOR_API_BASE` from `FE/config.js`:
- Localhost: `http://127.0.0.1:8000`
- Production: `https://ipoor.hanzomaster.dev/api`

Override by setting `window.IPOOR_API_BASE` before scripts load.
