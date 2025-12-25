from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import routers
from .config import get_settings
from .database import engine

settings = get_settings()

app = FastAPI(
    title="iPOOR API",
    version="0.1.0",
    description="Backend services for the iPOOR platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(routers.health.router)
app.include_router(routers.auth.router)
app.include_router(routers.households.router)
app.include_router(routers.policies.router)
app.include_router(routers.data_collections.router)
app.include_router(routers.activity_logs.router)
app.include_router(routers.files.router)
app.include_router(routers.gis.router)
app.include_router(routers.dashboard.router)
app.include_router(routers.locations.router)

app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "iPOOR API is running", "env": settings.app_env}
