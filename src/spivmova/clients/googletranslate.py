import html
import re

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.auth.exceptions import RefreshError
from google.cloud import translate_v3 as translate

from spivmova.clients.translator import (
    ContextualTranslation,
    ContextUnit,
    Translation,
    TranslationElement,
    TranslationError,
)
from spivmova.config import settings

# Regex patterns to extract the line and word translations from the tagged HTML
WORD_RE = r"<w id='([^']+)'>([^<]+)</w>"
SENTENCE_RE = r"<p class='context'>([^<]+)</p>"


class GoogleTranslateClient:
    """
    Google Translate v3 client.
    Bills for every character translated.
    Does not natively support context hints, but does support HTML translation.
    """
    def __init__(self):
        self.client = translate.TranslationServiceAsyncClient()

    async def batch_translate(
        self,
        contents: list[str],
        target_language: str = "en",
        source_language_code: str | None = "uk",
    ) -> translate.TranslateTextResponse:
        """
        Single translation call of separate packages (strings)

        Separate packages are translated independently.
        """
        parent = f"projects/{settings.google_cloud_project_id}/locations/global"

        try:
            response = await self.client.translate_text(
                request={
                    "parent": parent,
                    "contents": contents,
                    "target_language_code": target_language,
                    "source_language_code": source_language_code,
                }
            )
        # Raise errors if call fails
        except GoogleAPICallError as e:
            raise TranslationError(
                message=f"Google {e.code}: {e.message}", retryable=e.code in (429, 500, 503, 504)
            ) from e
        except RetryError as e:
            raise TranslationError(f"Google: retries exhausted: {e}", retryable=True) from e
        except RefreshError as e:
            raise TranslationError(f"Google auth failed: {e}") from e

        return response

    async def contextual_batch_translate(
        self,
        context_units: list[ContextUnit],
        target_lang: str = "en",
        source_lang: str | None = "uk",
    ) -> list[ContextualTranslation]:
        """
        ContextUnits -> HTML (batch translated) -> ContextualTranslations

        Google Translate doesn't have a separate context parameter.
        Google Translate does have HTML translation support, which leaves
        HTML structure unchanged but translates raw text. 
        Embedding the context and the words with separate element tags, 
        allows for elements to be translated with the global context but at the element level.

        The context of the element structure is partially preserved,
        identical words in a sentence with different sense's may keep their correct sense.
        Ex: "The financial bank on the river bank"
        word1: The -> le
        word2: financial -> financière
        word3: bank -> banque
        ...
        word6: river -> rivière
        word7: bank -> bord
        """

        # Convert context units to HTML with tags for context driven translation
        html_formatted_lines = []
        for unit in context_units:
            html_element = f"<p class='context'>{html.escape(unit.context)}</p><p class='words'>"
            for el in unit.elements:
                html_element += f"<w id='{el.position}'>{html.escape(el.text)}</w>"
            html_element += "</p>"
            html_formatted_lines.append(html_element)

        # Batched translation call
        response = await self.batch_translate(html_formatted_lines, target_lang, source_lang)

        # Parse HTML response to extract translations
        translations = []
        if len(context_units) != len(response.translations):
            raise TranslationError(
                "Translation count mismatch: "
                f"{len(response.translations)} line translations for {len(context_units)} lines."
            )
        for unit, translation in zip(context_units, response.translations, strict=True):
            # Extract context (line) translation
            context_translated = re.search(SENTENCE_RE, translation.translated_text)
            if not context_translated:
                raise TranslationError(
                    f"Could not find context in translation: {translation.translated_text}"
                )
            context = Translation(
                translation=html.unescape(context_translated.group(1)), source=unit.context
            )

            # Extract all element (word) translations
            translated = dict(re.findall(WORD_RE, translation.translated_text))
            missing = [el.position for el in unit.elements if str(el.position) not in translated]
            # Verify all tokens got translated (NOTE: Google may merge of drop <w> tags)
            if missing:
                raise TranslationError(
                    f"Missing word ids {missing} in: {translation.translated_text}"
                )
            elements = [
                TranslationElement(
                    position=el.position,
                    source=el.text,
                    translation=html.unescape(translated[str(el.position)]),
                )
                for el in unit.elements
            ]

            # Assemble the translated object
            translations.append(
                ContextualTranslation(
                    context=context,
                    elements=elements,
                    source_language=translation.detected_language_code or source_lang,
                    target_language=target_lang,
                    provider="google",
                )
            )

        return translations


# {
#   "translations": [
#     {
#       "translatedText": "string",
#       "model": "string",
#       "detectedLanguageCode": "string",
#       "glossaryConfig": {
#         "object (TranslateTextGlossaryConfig)"
#       }
#     }
#   ],
#   "glossaryTranslations": [
#     {
#       "translatedText": "string",
#       "model": "string",
#       "detectedLanguageCode": "string"
#     }
#   ]
# }