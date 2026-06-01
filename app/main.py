from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database import engine
from app.models import Base
from app.routers import orders, billing, inventory

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Café Management API",
    description="Backend for managing café orders, billing, and AI-powered inventory.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(orders.router)
app.include_router(billing.router)
app.include_router(inventory.router)

# Serve frontend
frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse("frontend/index.html")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Database integrity error — possible duplicate entry."})


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "café-management-api"}
