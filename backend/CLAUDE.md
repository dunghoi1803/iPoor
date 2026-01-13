# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head                                  # Apply all migrations
alembic revision --autogenerate -m "describe change"  # Generate migration from model changes

# Seed data
python -m app.seeds.seed_all           # Run all seeders
python -m app.seeds.sample_households  # Households only
python -m app.seeds.sample_policies    # Policies only
python -m app.seeds.sample_users       # Users only
python -m app.seeds.sample_activity_logs  # Activity logs only
```

## Architecture

### Directory Structure

```
app/
├── main.py          # FastAPI app bootstrap, middleware, router includes
├── config.py        # Settings from environment (pydantic-settings)
├── constants.py     # Enums: Roles, PovertyStatus, CollectionStatus, PolicyCategory
├── database.py      # SQLAlchemy engine and SessionLocal
├── deps.py          # FastAPI dependencies: get_db, get_current_user, authenticate_user
├── routers/         # API route handlers
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic request/response schemas
├── seeds/           # Demo data seeders
└── utils/           # Helpers: security, file_naming, household_code, activity_log
```

### Key Patterns

**Dependency Injection**:
- `get_db` - yields SQLAlchemy session
- `get_current_user` - extracts user from JWT, requires authentication
- `authenticate_user(db, email, password)` - validates credentials

**Models to Routers Mapping**:
| Model | Router | Prefix |
|-------|--------|--------|
| User | auth | `/auth` |
| Household | households | `/households` |
| Policy, PolicyDraft | policies | `/policies` |
| DataCollection | data_collections | `/data-collections` |
| ActivityLog | activity_logs | `/activity-logs` |
| - | files | `/files` |
| - | gis | `/gis` |
| - | dashboard | `/dashboard` |
| - | locations | `/locations` |

**Role-Based Access** (from `constants.py`):
- `admin` - Full access
- `province_officer` - Province-level operations
- `district_officer` - District-level operations
- `commune_officer` - Commune-level operations

**File Uploads**:
- Directory: `UPLOAD_DIR` env var (default: `uploads/`)
- Served at: `/files/<path>` via FastAPI StaticFiles
- Subfolders: `users/` (CCCD images), policies, etc.

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Docker Value |
|----------|-------------|--------------|
| `DB_HOST` | MySQL host | `db` (container name) |
| `DB_PORT` | MySQL port | `3306` |
| `DB_USER` | MySQL user | `root` |
| `DB_PASSWORD` | MySQL password | Set in compose |
| `DB_NAME` | Database name | `iPoor` |
| `JWT_SECRET` | Token signing key | Strong random string |
| `ALLOWED_ORIGINS` | CORS whitelist | `http://localhost:3000` |
| `UPLOAD_DIR` | File upload path | `uploads` |
| `ADMIN_EMAIL` | Initial admin email | - |
| `ADMIN_PASSWORD` | Initial admin password | - |

### GIS Data Integration

The backend reads GIS data from `FE/data/processed/`:
- `gis_indicator_values.csv`
- `region_map.json`

**Build Note**: The Dockerfile copies these files during image build. When building outside docker-compose, run from repo root:
```bash
docker build -f backend/Dockerfile -t ipoor-api .
```

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Security Notes

- Passwords hashed with bcrypt (72-byte limit handled via clamping)
- JWT tokens expire per `JWT_EXPIRE_MINUTES` (default: 60)
- CORS configured via `ALLOWED_ORIGINS`
