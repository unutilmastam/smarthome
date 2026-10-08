from fastapi import APIRouter

from app.api.v1 import (
    auth, automations, cameras, commands, devices, energy, events, health, homes, hub, hubs, notifications, realtime,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(homes.router)
api_router.include_router(devices.router)
api_router.include_router(hubs.router)
api_router.include_router(commands.router)
api_router.include_router(hub.router)
api_router.include_router(realtime.router)
api_router.include_router(energy.router)
api_router.include_router(cameras.router)
api_router.include_router(events.router)
api_router.include_router(automations.router)
api_router.include_router(notifications.router)
