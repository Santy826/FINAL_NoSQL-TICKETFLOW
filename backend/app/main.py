from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import lifespan
from app.api.router import api_router

app = FastAPI(
    title="TicketFlow API",
    version="0.1.0",
    description="API REST para gestión de eventos y boletería",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "TicketFlow API"}
