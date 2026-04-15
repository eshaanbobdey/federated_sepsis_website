from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
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

# CORS — update with your Netlify URL after deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",  # Local development
        "http://127.0.0.1:5500",
        # Add your Netlify URL here after deployment, e.g.:
        # "https://your-site.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(weights.router)
app.include_router(aggregate.router)


@app.get("/")
async def root():
    return {"message": "FedSepsis API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
