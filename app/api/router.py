from fastapi import APIRouter

from app.api import auth, config, dashboard, incidents, inventory, sites

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sites.router)
api_router.include_router(incidents.router)
api_router.include_router(config.router)
api_router.include_router(inventory.router)
api_router.include_router(dashboard.router)
