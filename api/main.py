"""
GovPulse API — FastAPI application entry point
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.config import ALLOWED_ORIGINS
from api.auth import authenticate_user, create_access_token, get_current_user
from api.models import LoginRequest, LoginResponse
from api.routes import stories, brief, responses, pipeline
from api.routes import stories, brief, responses, pipeline, response_generate

app = FastAPI(
    title="GovPulse API",
    description="Government Media Intelligence Platform — API",
    version="1.0.0",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "app": "GovPulse API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """Login and receive a JWT token."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(req.username)

    return LoginResponse(
        access_token=token,
        name=user.get("name", req.username),
        role=user.get("role", "viewer"),
        ministry=user.get("ministry"),
    )


@app.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    """Return the current user's info."""
    return {
        "username": user.get("username"),
        "name": user.get("name"),
        "role": user.get("role"),
        "ministry": user.get("ministry"),
    }


# Attach route modules
app.include_router(stories.router)
app.include_router(brief.router)
app.include_router(responses.router)
app.include_router(pipeline.router)
app.include_router(response_generate.router)