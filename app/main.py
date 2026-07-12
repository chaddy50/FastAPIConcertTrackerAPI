from fastapi import FastAPI
from fastapi.routing import APIRouter

from app.routers import auth, composers, performances, performers, set_list_entries, venues, works

app = FastAPI()

v1 = APIRouter()
v1.include_router(auth.router)
v1.include_router(venues.router)
v1.include_router(composers.router)
v1.include_router(performers.router)
v1.include_router(works.router)
v1.include_router(performances.router)
v1.include_router(set_list_entries.router)

app.include_router(v1, prefix="/v1")
