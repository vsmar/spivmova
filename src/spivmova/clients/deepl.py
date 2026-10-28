from asyncio import Semaphore, gather

import httpx
from pydantic import BaseModel, Field

from spivmova.clients.translator import (
    ContextualTranslation,
    ContextUnit,
    Translation,
    TranslationElement,
    TranslationError,
)
from spivmova.config import settings

# DeepL requires a region for english, portuguese, and a script tag for chinese
_TARGET_DEFAULT_REGION = {"en": "EN-US", "pt": "PT-PT", "zh": "ZH-HANS"}


def _to_deepl_source(tag: str | None) -> str | None:
    return tag.split("-")[0].upper() if tag else None


def _to_deepl_target(tag: str) -> str:
    return _TARGET_DEFAULT_REGION.get(tag.lower(), tag.upper())


def _from_deepl_source(tag: str) -> str:
    return tag.lower()


class DeepLError(TranslationError):
    def __init__(self, status_code: int | None, message: str):
        super().__init__(
            message=f"DeepL {status_code}: {message}",
            retryable=status_code is None or status_code >= 500 or status_code in (429, 456),
            # 456 is quota exceeded
        )


def _error_from(r: httpx.Response) -> DeepLError:
    try:
        body = r.json()
        message = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        message = None
    return DeepLError(r.status_code, message or r.text[:200])


class DeepLTranslation(BaseModel):
    translated_text: str = Field(alias="text")
    source_lang: str = Field(alias="detected_source_language")


class DeepLClient:
    """
    DeepL v2 client. 
    
    Billing is per translated character. 
    The per-request `context` hint is never translated or billed. 
    The texts in a request can't see each other, only the shared context.
    """

    BASE_FREE = "https://api-free.deepl.com"
    BASE_PRO = "https://api.deepl.com"

    def __init__(self, http: httpx.AsyncClient):
        self._http = http
        self.base = self.BASE_FREE if settings.deepl_api_key.endswith(":fx") else self.BASE_PRO
        self._limit = Semaphore(5) # limits concurrent requests to avoid DeepL rate limiting

    async def _post(self, path: str, headers: dict[str, str], json: dict) -> httpx.Response:
        async with self._limit:
            try:
                r = await self._http.post(self.base + path, headers=headers, json=json)
            except httpx.RequestError as e:
                raise DeepLError(None, f"Unreachable: {e}") from e
        if not r.is_success:
            raise _error_from(r)
        return r

    async def translate_with_context(
        self,
        texts: list[str],
        target_lang: str = "EN-US",
        context: str | None = None,
        source_lang: str | None = "UK",
    ) -> list[DeepLTranslation]:
        """
        Translate texts in one request with an optional context hint. 
        Expects DeepL codes ("EN-US", "UK").
        """

        json = {"text": texts, "target_lang": target_lang}
        header = {"Authorization": f"DeepL-Auth-Key {settings.deepl_api_key}"}
        if source_lang is not None:
            json["source_lang"] = source_lang
        if context is not None:
            json["context"] = context

        r = await self._post(path="/v2/translate", headers=header, json=json)

        translations = [
            DeepLTranslation.model_validate(translation) for translation in r.json()["translations"]
        ]

        return translations

    async def contextual_batch_translate(
        self,
        context_units: list[ContextUnit],
        target_lang: str = "en",
        source_lang: str | None = "uk",
    ) -> list[ContextualTranslation]:
        """
        Batch (ContextUnit -> Translate with context -> ContextualTranslation)

        Each translated text has only the shared context and itself as context.
        If each text is a single word or is otherwise limited in context, 
        and shared context has homynyms present then it's ambiguous which sense 
        homonym text will take.
        """
        
        source_lang = _to_deepl_source(source_lang)

        results = await gather(
            *[
                self.translate_with_context(
                    texts=[context_unit.context] + [el.text for el in context_unit.elements],
                    target_lang=_to_deepl_target(target_lang),  # DeepL language id format
                    context=context_unit.context,
                    source_lang=source_lang,
                )
                for context_unit in context_units
            ]
        )

        translations = []
        for context_unit, result in zip(context_units, results, strict=True):
            if len(context_unit.elements) + 1 != len(result):
                raise TranslationError(
                    f"Translation count mismatch for context '{context_unit.context}': "
                    + f"{len(context_unit.elements)} elements, but {len(result)} translations."
                )

            context = Translation(
                source=context_unit.context, translation=result[0].translated_text
            )
            elements = [
                TranslationElement(
                    position=el.position,
                    source=el.text,
                    translation=result[i + 1].translated_text,
                )
                for i, el in enumerate(context_unit.elements)
            ]

            translations.append(
                ContextualTranslation(
                    context=context,
                    elements=elements,
                    source_language=_from_deepl_source(result[0].source_lang),
                    target_language=target_lang,
                    provider="deepl",
                )
            )

        return translations
