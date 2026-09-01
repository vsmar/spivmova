from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient
from spivmova.db.session import get_session


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http

HttpClient = Annotated[httpx.AsyncClient, Depends(get_http)]

def get_lrclib(http: HttpClient) -> LrclibClient:
    return LrclibClient(http)

def get_deepl(http: HttpClient) -> DeepLClient:
    return DeepLClient(http)

Lrclib = Annotated[LrclibClient, Depends(get_lrclib)]
Deepl = Annotated[DeepLClient, Depends(get_deepl)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
