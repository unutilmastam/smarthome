from fastapi import APIRouter

from app.api.v1 import auth, commands, devices, health, homes, hub, hubs

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(homes.router)
api_router.include_router(devices.router)
api_router.include_router(hubs.router)
api_router.include_router(commands.router)
api_router.include_router(hub.router)
