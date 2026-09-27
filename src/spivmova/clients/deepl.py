import warnings

import httpx
from pydantic import BaseModel, Field

from spivmova.config import settings


class DeepLError(Exception):
    def __init__(self, status_code: int, message: str, retry_after: float | None = None):
        super().__init__(f"DeepL {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after


def _error_from(r: httpx.Response) -> DeepLError:
    try:
        body = r.json()
        message = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        message = None
    try:
        retry_after = float(r.headers["Retry-After"])
    except (KeyError, ValueError):
        retry_after = None
    return DeepLError(r.status_code, message or r.text[:200], retry_after)


class DeepLTranslation(BaseModel):
    translated_text: str = Field(alias="text")
    source_lang: str = Field(alias="detected_source_language")


class DeepLClient:
    BASE_FREE = "https://api-free.deepl.com"
    BASE_PRO = "https://api.deepl.com"

    def __init__(self, http: httpx.AsyncClient):
        self._http = http
        self.base = self.BASE_FREE if settings.deepl_api_key.endswith(":fx") else self.BASE_PRO

    async def translate(
        self,
        text: str,
        target_lang: str,
        context: str | None = None,
        source_lang: str
        | None = "UK",  # NOTE: May want to support autodetection (needs to be robust)
    ) -> DeepLTranslation:
        translations = await self.translate_batch([text], target_lang, context, source_lang)
        return translations[0]


    async def translate_batch(
        self,
        texts: list[str],
        target_lang: str,
        context: str | None = None,
        source_lang: str | None = "UK",
    ) -> list[DeepLTranslation]:
        json = {"text": texts, "target_lang": target_lang}
        header = {"Authorization": f"DeepL-Auth-Key {settings.deepl_api_key}"}
        if source_lang is not None:
            json["source_lang"] = source_lang
        if context is not None:
            json["context"] = context
        r = await self._http.post(self.base + "/v2/translate", headers=header, json=json)
        if not r.is_success:
            raise _error_from(r)

        translations = [
            DeepLTranslation.model_validate(translation) for translation in r.json()["translations"]
        ]

        # NOTE: May want to scrap this
        for translation in translations:
            if translation.source_lang != "UK":
                warnings.warn(
                    "Detected source language was not Ukrainian (UK), "
                    + f"but {translation.source_lang}.",
                    stacklevel=2,
                )

        return translations
