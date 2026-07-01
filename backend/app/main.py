from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import engine, Base
from app.api.routes import upload, evaluate, report, study_plan, students, insights
from app.api.routes.upload import textbook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev only – use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="StudyAI API",
    description="AI-powered exam evaluator, study coach, and academic analytics platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(upload.router)
app.include_router(textbook_router)
app.include_router(evaluate.router)
app.include_router(report.router)
app.include_router(study_plan.router)
app.include_router(insights.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": "StudyAI"}
