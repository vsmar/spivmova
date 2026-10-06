import re
import warnings

from google.cloud import translate_v3 as translate
from pydantic import BaseModel, Field

from spivmova.config import settings

WORD_RE = r"<w id='([^']+)'>([^<]+)</w>"
SENTENCE_RE = r"<p class='context'>([^<]+)</p>"

class GoogleTranslation(BaseModel):
    translated_text: str = Field(alias="translatedText")
    source_lang: str = Field(alias="detectedLanguageCode")
    model: str = Field(alias="model")


#       "translatedText": "string",
#       "model": "string",
#       "detectedLanguageCode": "string",


class GoogleTranslateClient:
    def __init__(self):
        self.client = translate.TranslationServiceClient()

    async def synchronous_batch_translate(
        self,
        contents: list[str],
        target_language: str | None = "en",
        source_language_code: str | None = "uk"
    ) -> translate.TranslateTextResponse:
        location = "global"  # or a specific region like "us-central1"
        parent = f"projects/{settings.google_cloud_project_id}/locations/{location}"

        response = self.client.translate_text(
            request={
                "parent": parent,
                "contents": contents,
                "target_language_code": target_language,
                "source_language_code": source_language_code,
            }
        )
                    
        return response

    async def contextual_batch_translate(
        self,
        texts: list[list[str]],
        target_lang: str | None = "en",
        context: str | None = None,
        source_lang: str | None = "uk",
    ) -> list[GoogleTranslation]:

        html_formatted_lines = []
        for sentence, words in zip(context, texts, strict=True):
            html_element = f"<p class='context'>{sentence}</p><p class='words'>"
            for i, word in enumerate(words):
                html_element += f"<w id='{i}'>{word}</w>"
            html_element += "</p>"
            html_formatted_lines.append(html_element)        

        formatted_lines = await self.synchronous_batch_translate(html_formatted_lines, target_lang, source_lang)

        sentences = []
        words_list = []
        detected_lang = []

        for html_line in formatted_lines.translations:
            # html.unescape()
            # html.escape()
            sentences.append(re.search(SENTENCE_RE, html_line.translated_text).group(1))
            words_list.append(re.findall(WORD_RE, html_line.translated_text))
            detected_lang.append(html_line.detected_language_code)

        return (sentences, words_list, detected_lang)


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
