# iPoor
MIS for Poverty Reduction

## Quick start (Docker)

1) Ensure `backend/.env` exists and matches the DB container:

```
DB_HOST=db
DB_PORT=3306
DB_USER=root
DB_PASSWORD=18032002
DB_NAME=iPoor
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

2) Build + run:

```bash
docker compose up -d --build
```

3) Open:
   - Frontend: `http://localhost:3000/LandingPage/index.html`
   - Backend: `http://localhost:8000/docs`

## Seed demo data

Run inside the API container:

```bash
docker exec -it ipoor_api sh -c "cd /app && python -m app.seeds.seed_all"
```

## Reset DB (only when passwords/DB name changed)

This will delete all data:

```bash
docker compose down
docker volume rm ipoor_ipoor_db_data
docker compose up -d --build
```

Then re-seed:

```bash
docker exec -it ipoor_api sh -c "cd /app && python -m app.seeds.seed_all"
```

## GIS/Dashboard data

API reads data from:

- `FE/data/processed/gis_indicator_values.csv`
- `FE/data/processed/region_map.json`

The GIS data is embedded into the backend Docker image during build. If you update the CSV/JSON files, rebuild the API image:

```bash
docker compose up -d --build api
```

## Standalone Docker builds (without docker-compose)

The backend Dockerfile uses the **repo root** as its build context to access `FE/data`. When building standalone images:

```bash
# Backend API - must run from repo root
docker build -f backend/Dockerfile -t ipoor-api .

# Frontend - can run from FE directory
cd FE && docker build -t ipoor-fe .
```

Do NOT build the backend from inside the `backend/` directory, as it needs access to `FE/data` for GIS endpoints.

## Public demo via Cloudflare Tunnel (no domain)

1) Run two tunnels:

```bash
cloudflared.exe tunnel --url http://localhost:3000
cloudflared.exe tunnel --url http://localhost:8000
```

2) Update FE API base:

`FE/config.js`:

```js
window.IPOOR_API_BASE = "https://<api-trycloudflare-url>";
```

3) Allow CORS for the FE URL:

`backend/.env`:

```
ALLOWED_ORIGINS=https://<fe-trycloudflare-url>,http://localhost:3000,http://127.0.0.1:3000
```

4) Rebuild:

```bash
docker compose up -d --build
```
