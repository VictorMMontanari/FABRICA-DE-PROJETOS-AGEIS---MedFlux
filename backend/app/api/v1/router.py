from fastapi import APIRouter

from app.api.v1.routes import agents, auth, files, health_units, triage, users, vector

api_router = APIRouter()
for module in (auth, users, health_units, triage, agents, vector, files):
    api_router.include_router(module.router)
