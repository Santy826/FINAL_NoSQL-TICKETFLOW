"""Punto de entrada de la API."""

from fastapi import FastAPI

app = FastAPI(
    title="TicketFlow API",
    version="0.1.0",
    description="API REST para gestión de eventos y boletería.",
)
