from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ...config import settings

def configure_cors(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
