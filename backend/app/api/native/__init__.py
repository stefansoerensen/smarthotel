"""The native API under ``/api``."""

from fastapi import APIRouter

from app.api.native import auth, commands, devices, estate, twin

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(estate.router)
api_router.include_router(devices.router)
api_router.include_router(twin.router)
api_router.include_router(commands.router)
