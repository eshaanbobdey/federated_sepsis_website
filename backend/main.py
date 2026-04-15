from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.config import FRONTEND_DIR
from backend.routes import auth, weights, aggregate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    await init_db()
    yield


app = FastAPI(
    title="FedSepsis — Federated Learning Sepsis Detection",
    description="Privacy-preserving collaborative sepsis detection platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend on same origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(weights.router)
app.include_router(aggregate.router)

# Serve frontend static files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
