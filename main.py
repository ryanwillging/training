"""Training API - FastAPI app for Vercel."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Training Optimization System API",
    version="0.1.0"
)

@app.get("/")
def root():
    return {"message": "Training API is running!", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/test")
def test():
    return {"test": "success"}
