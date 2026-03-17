"""
SnipShot Database API - Supabase Edition

This service handles:
- User registration/login (via Supabase Auth)
- JWT authentication (Supabase tokens)
- Image storage (Supabase Storage)
- Image metadata CRUD (Supabase PostgreSQL)

All-in-one Supabase backend.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from supabase import create_client, Client

from database import init_db
from routes import users_router, images_router, folders_router

load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    await init_db()
    if supabase:
        print("✅ Supabase connected")
    else:
        print("⚠️ Supabase not configured (check SUPABASE_URL and SUPABASE_ANON_KEY)")
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")


app = FastAPI(
    title="SnipShot Database API",
    description="User management and image storage via Supabase",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(users_router, prefix="/api")
app.include_router(folders_router, prefix="/api")
app.include_router(images_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    for route in app.routes:
        print(f"Route: {route.path} {route.methods}")

@app.get("/")
def root():
    return {
        "service": "SnipShot Database API",
        "version": "2.0.0",
        "backend": "Supabase",
        "endpoints": {
            "/api/users/register": "POST - Register new user",
            "/api/users/login": "POST - Login → JWT",
            "/api/users/me": "GET - Get profile",
            "/api/images": "GET - List user's images",
            "/api/images": "POST - Upload image to Supabase Storage",
            "/api/images/{id}": "GET - Get image details",
            "/api/images/{id}": "DELETE - Delete image"
        }
    }


@app.get("/health")
def health():
    return {"ok": True, "service": "database-api", "backend": "supabase"}
