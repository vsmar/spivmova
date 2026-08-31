from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.lrclib import LrclibClient
from spivmova.db.session import get_session


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http

HttpClient = Annotated[httpx.AsyncClient, Depends(get_http)]

def get_lrclib(http: HttpClient) -> LrclibClient:
    return LrclibClient(http)

Lrclib = Annotated[LrclibClient, Depends(get_lrclib)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
