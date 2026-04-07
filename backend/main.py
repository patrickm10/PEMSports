import sys
import os
from pathlib import Path

# Add the project root (parent of 'backend') to sys.path
# This allows 'import backend.api...' to work even if run as 'python backend/main.py'
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router as api_router
from backend.api.v1.rankings import router as v1_router

app = FastAPI(title="NFL Stats Analyzer API")

@app.get("/")
def read_root():
    return {"message": "NFL Stats Analyzer API is running. Visit /docs for documentation.", "version": "1.0.0"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardize static file mounting
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Mount API routes — V1 takes precedence over legacy
app.include_router(v1_router, prefix="/api/v1/rankings", tags=["rankings"])
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
