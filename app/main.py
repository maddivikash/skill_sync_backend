from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import user, goal, path, step, task, dashboard, catalog
from app.core.config import settings
from app.db.session import engine
from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev-only shortcut. In prod, tables are managed by Alembic migrations
    # (run via entrypoint.sh). Catalog seeding also happens in entrypoint.sh
    # (once, before workers) to avoid per-worker races.
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SkillSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health():
    # Liveness probe for ECS / EKS / load balancer target group.
    return {"status": "ok", "env": settings.APP_ENV}


app.include_router(user.router, prefix="/api")
app.include_router(goal.router)
app.include_router(path.router)
app.include_router(step.router)
app.include_router(task.router)
app.include_router(dashboard.router)
app.include_router(catalog.router)
