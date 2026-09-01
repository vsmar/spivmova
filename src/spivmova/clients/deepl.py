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
        self, text: str, target_lang: str, context: str | None = None
    ) -> DeepLTranslation:
        json = {"text": [text], "target_lang": target_lang}
        header = {"Authorization": f"DeepL-Auth-Key {settings.deepl_api_key}"}

        if context is not None:
            json["context"] = context
        r = await self._http.post(self.base + "/v2/translate", headers=header, json=json)
        r.raise_for_status()

        translation = DeepLTranslation.model_validate(r.json()["translations"][0])
        if translation.source_lang != "UK":
            warnings.warn(
                "Detected source language was not Ukrainian (UK), "
                + f"but {translation.source_lang}.",
                stacklevel=2,
            )

        return translation
