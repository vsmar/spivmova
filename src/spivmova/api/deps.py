from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient
from spivmova.clients.translator import ContextualTranslator
from spivmova.clients.youtube import YouTubeClient
from spivmova.db.session import get_session


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


HttpClient = Annotated[httpx.AsyncClient, Depends(get_http)]


def get_lrclib(http: HttpClient) -> LrclibClient:
    return LrclibClient(http)


def get_youtube(http: HttpClient) -> YouTubeClient:
    return YouTubeClient(http)


def get_translator(request: Request, http: HttpClient) -> ContextualTranslator:
    # TODO: provider = request.query_params.get("provider") or a user setting
    google = request.app.state.google
    if google is not None:
        return google
    return DeepLClient(http)


Lrclib = Annotated[LrclibClient, Depends(get_lrclib)]
YouTube = Annotated[YouTubeClient, Depends(get_youtube)]
DbSession = Annotated[AsyncSession, Depends(get_session)]
Translator = Annotated[ContextualTranslator, Depends(get_translator)]
