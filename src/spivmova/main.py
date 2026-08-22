from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx


USER_AGENT = "spivmova v0.1.0 (https://github.com/vsmar/spivmova)"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(10.0),
    )
    yield
    await app.state.http.aclose()