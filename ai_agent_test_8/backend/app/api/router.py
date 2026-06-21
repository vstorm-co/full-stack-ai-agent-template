"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes.v1 import v1_router

api_router = APIRouter()

# API v1 routes (prefix is set in main.py via settings.API_V1_STR)
api_router.include_router(v1_router)
