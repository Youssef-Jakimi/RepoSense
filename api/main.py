import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import ingest, status, qa, review

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="RepoSense API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # dev only; tighten if deploying
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(review.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
