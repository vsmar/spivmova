import warnings

import httpx
from pydantic import BaseModel, Field

from spivmova.config import settings


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
        r.raise_for_status()

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
