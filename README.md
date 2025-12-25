# iPoor
MIS for Poverty Reduction

## Run with Docker

1. Ensure `backend/.env` is set (DB_HOST should be `db` for Docker).
   If you change `DB_PASSWORD` or `DB_NAME`, also set them as environment
   variables or in a root `.env` so `docker compose` uses the same values.
2. Start services:

```bash
docker compose up -d --build
```

3. Open:
   - Frontend: `http://localhost:3000/LandingPage/index.html`
   - Backend: `http://localhost:8000/docs`

## Seed demo data

Run inside the API container:

```bash
docker exec -it ipoor_api sh -c "cd /app && python -m app.seeds.seed_all"
```
