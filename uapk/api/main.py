"""
FastAPI Application for OpsPilotOS
Main API server with all endpoints.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Any, Dict

from uapk.manifest_schema import UAPKManifest
from uapk.db import init_db, get_session
from uapk.policy import init_policy_engine
from uapk.tax import init_tax_calculator


# Global manifest (set during startup)
_manifest: UAPKManifest | None = None


def get_manifest() -> UAPKManifest:
    """Get the loaded manifest"""
    if _manifest is None:
        raise RuntimeError("Manifest not loaded")
    return _manifest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    print("[OpsPilotOS] Initializing database...")
    init_db()

    print("[OpsPilotOS] System ready")
    yield

    # Shutdown
    print("[OpsPilotOS] Shutting down...")


def create_app(manifest: UAPKManifest) -> FastAPI:
    """Create FastAPI application with loaded manifest"""
    global _manifest
    _manifest = manifest

    # Import routers after manifest is set (avoids circular import)
    from uapk.api import auth, organizations, projects, deliverables, billing, hitl, nft_routes, metrics

    # Initialize subsystems
    init_policy_engine(manifest)
    init_tax_calculator(manifest.corporateModules.taxOps)

    # Create app
    app = FastAPI(
        title="OpsPilotOS API",
        description="Autonomous SaaS Business-in-a-Box",
        version="0.1.0",
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(organizations.router, prefix="/orgs", tags=["organizations"])
    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    app.include_router(deliverables.router, prefix="/deliverables", tags=["deliverables"])
    app.include_router(billing.router, prefix="/billing", tags=["billing"])
    app.include_router(hitl.router, prefix="/hitl", tags=["hitl"])
    app.include_router(nft_routes.router, prefix="/nft", tags=["nft"])
    app.include_router(metrics.router, prefix="", tags=["system"])

    # Root endpoint
    @app.get("/")
    def root():
        return {
            "name": manifest.name,
            "description": manifest.description,
            "version": manifest.uapkVersion,
            "executionMode": manifest.executionMode,
            "status": "running"
        }

    # Health check
    @app.get("/healthz")
    def healthz():
        return {"status": "healthy"}

    return app
