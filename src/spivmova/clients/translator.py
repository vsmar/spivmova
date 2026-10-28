# Holds the data models used for translation request and responses
from typing import Protocol

from pydantic import BaseModel


class ElementInput(BaseModel):
    position: int
    text: str


class ContextUnit(BaseModel):
    context: str
    elements: list[ElementInput]


class Translation(BaseModel):
    source: str
    translation: str


class TranslationElement(Translation):
    position: int


class ContextualTranslation(BaseModel):
    context: Translation
    elements: list[TranslationElement]
    source_language: str
    target_language: str
    provider: str | None


class TranslationError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


# translation.py
class ContextualTranslator(Protocol):
    async def contextual_batch_translate(
        self,
        context_units: list[ContextUnit],
        target_lang: str = "en",
        source_lang: str | None = "uk",
    ) -> list[ContextualTranslation]: ...
