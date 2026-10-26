from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.core.config import settings
from app.core.database import Base, engine
import app.models  # register SQLAlchemy metadata

# For quick local boot only. Production should use Alembic migrations as a deployment step.
if settings.app_env == "development":
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediTrack API", version="0.1.0", description="Personal health routine reminders and check-ins")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"], allow_headers=["Authorization","Content-Type"])
app.include_router(router, prefix="/api/v1")

@app.get("/health/live", tags=["health"])
def live(): return {"status":"ok"}

@app.get("/health/ready", tags=["health"])
def ready():
    from sqlalchemy import text
    from app.core.database import SessionLocal
    with SessionLocal() as db: db.execute(text("SELECT 1"))
    return {"status":"ready"}
