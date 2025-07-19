from fastapi import FastAPI
from app.api.routes import user
from app.models.user import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(user.router, prefix="/api")
