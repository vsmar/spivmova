from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from spivmova.api.routes import router
from spivmova.clients.googletranslate import GoogleTranslateClient
from spivmova.config import settings

USER_AGENT = "spivmova v0.1.0 (https://github.com/vsmar/spivmova)"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(10.0),
    )
    if settings.google_cloud_project_id:
        app.state.google = GoogleTranslateClient()
    yield
    if settings.google_cloud_project_id:
        await app.state.google.client.transport.close()
    await app.state.http.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
