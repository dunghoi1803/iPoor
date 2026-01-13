# iPoor
MIS for Poverty Reduction

## Local Docker (recommended)

1) Create `backend/.env`:

```
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=18032002
DB_NAME=iPoor
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

2) Persist uploads on host (avoid losing images on rebuild):

In `docker-compose.yml` (service `api`):

```yaml
services:
  api:
    volumes:
      - ./backend/uploads:/app/uploads
```

Create the folder:

```bash
mkdir -p backend/uploads
```

3) Build + run:

```bash
docker compose up -d --build
```

4) Open:
   - Frontend: `http://localhost:3000/LandingPage/index.html`
   - Backend: `http://localhost:8000/docs`

## Seed demo data

```bash
docker compose exec api sh -c "cd /app && python -m app.seeds.seed_all"
```

## Reset DB (only when DB name/password changed)

```bash
docker compose down
docker volume rm ipoor_ipoor_db_data
docker compose up -d --build
```

Then re-seed:

```bash
docker compose exec api sh -c "cd /app && python -m app.seeds.seed_all"
```

## Rebuild only API (GIS data updated)

```bash
docker compose up -d --build api
```

## Production / Coolify

1) Configure environment in Coolify (or `backend/.env` on server):

```
DB_HOST=<prod-db-host>
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<prod-password>
DB_NAME=<prod-db-name>
ALLOWED_ORIGINS=https://ipoor.hanzomaster.dev
```

2) Persist uploads in production:

```yaml
services:
  api:
    volumes:
      - ./backend/uploads:/app/uploads
```

3) FE config auto-detects local vs prod. Optional override:

```js
window.IPOOR_API_BASE = "https://ipoor.hanzomaster.dev/api";
```

4) Deploy:

```bash
docker compose up -d --build
```

## Standalone Docker builds (no compose)

Backend uses repo root as build context (needs `FE/data`):

```bash
docker build -f backend/Dockerfile -t ipoor-api .
cd FE && docker build -t ipoor-fe .
```
