import httpx
import respx

from spivmova.clients.lrclib import LrclibClient
from spivmova.clients.translator import (
    ContextualTranslation,
    ContextUnit,
    Translation,
    TranslationElement,
)
from spivmova.db.repository import get_track_by_lrclib_id
from spivmova.services.ingestion import ingest_track

LYRICS = (
    "[00:01.00] Колилили настане день день "
    + "\n\n[00:05.00]\n[00:08.00]Обійми мене, обійми мене, обійми обійми"
    + "\n[00:14.70][00:18.35] Так лагідно, і не пускай!?. "
    + "\n[00:22.00] Обійми мене, обійми мене, обійми обійми"
    + "\n[00:28.00] ♪♪"
)

LRCLIB_ID = -18


class DummyTranslator:
    def __init__(self):
        self.calls: list[list[ContextUnit]] = []

    async def contextual_batch_translate(
        self,
        context_units: list[ContextUnit],
        target_lang: str = "en",
        source_lang: str | None = "uk",
    ) -> list[ContextualTranslation]:
        self.calls.append(context_units)

        return [
            ContextualTranslation(
                context=Translation(source=u.context, translation=f"«{target_lang}: {u.context}»"),
                elements=[
                    TranslationElement(
                        position=el.position,
                        source=el.text,
                        translation=f"«{target_lang}: {el.text}»",
                    )
                    for el in u.elements
                ],
                source_language=source_lang or "uk",
                target_language=target_lang,
                provider="dummy",
            )
            for u in context_units
        ]


async def test_ingest_dedups_and_maps_translations(db_session):
    translator = DummyTranslator()
    with respx.mock(base_url="https://lrclib.net/api") as mock:
        mock.get("/get").respond(404)
        mock.get("/search").respond(
            200,
            json=[
                {
                    "id": LRCLIB_ID,
                    "trackName": "Обіймими",
                    "artistName": "Океан Ельзизи",
                    "duration": 245,
                    "syncedLyrics": LYRICS,
                },
            ],
        )

        async with httpx.AsyncClient() as http:
            client = LrclibClient(http)
            result = await ingest_track(db_session, client, translator, "Обіймими", "Okean Elzyzy")
            # idempotency test
            result2 = await ingest_track(db_session, client, translator, "Обіймими", "Okean Elzyzy")

    # db_session.expunge_all() # NOTE: seems to work without expunging token's sense and vocab
    track = await get_track_by_lrclib_id(db_session, LRCLIB_ID)
    lines = sorted(track.lines, key=lambda line: line.position)

    # Check the results
    assert result is not None
    assert result.lrclib_id == LRCLIB_ID
    assert result2 is not None
    assert result.id == result2.id

    # check translation call numbers (1 call, 3 lines)
    assert len(translator.calls) == 1
    assert len(translator.calls[0]) == 3
    # check that the db has 7 lines
    assert len(lines) == 7
    # check that the db has lines 2 & 5 and 3 & 4 with same translation_id but unique lines
    assert lines[2].translation_id == lines[5].translation_id
    assert lines[3].translation_id == lines[4].translation_id
    assert lines[2].id != lines[5].id
    assert {t.id for t in lines[2].tokens}.isdisjoint(t.id for t in lines[5].tokens)
    # line 1 should have no translation or tokens
    assert lines[1].translation is None
    assert lines[1].tokens == []
    # check line 0
    assert lines[0].time == 1000
    assert lines[0].text == "Колилили настане день день"
    assert lines[0].translation.translation == "«en: Колилили настане день день»"
    assert lines[0].tokens[0].text == "Колилили"
    assert lines[0].tokens[0].sense.translation == "«en: Колилили»"
    # Check that line 6 has no translation or tokens
    assert lines[6].translation is None
    assert lines[6].tokens == []
    # Check that tokens contain alphanumeric characters
    assert all(any(c.isalnum() for c in t.text) for line in lines for t in line.tokens)
    # Check that calls arent passing punct as elements
    for call in translator.calls:
        for unit in call:
            for el in unit.elements:
                assert el.text not in {",", ".", "!", "?"}
