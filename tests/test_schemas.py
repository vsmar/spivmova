import httpx
import respx

from spivmova.api.schemas import TrackOut
from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient
from spivmova.db.repository import get_track_by_lrclib_id
from spivmova.services.ingestion import ingest_track


async def test_ingest_track_with_single_song(db_session):
    with respx.mock(base_url="https://lrclib.net/api") as mock_lrclib:
        mock_lrclib.get("/get").respond(404)
        mock_lrclib.get("/search").respond(200, json=[
            {"id": 1, "trackName": "Обійми", "artistName": "Океан Ельзи",
             "duration": 245, "syncedLyrics": "[00:21.50] Обійми мене"},
        ])
        # TODO: add handling for free vs pro DeepL API url (or force .env?)
        async with respx.mock(base_url="https://api-free.deepl.com") as mock_deepl:
            mock_deepl.post('v2/translate').respond(200, json={
                "translations": [
                    {"text": "Embrace me", "detected_source_language": "UK"}
                ]
            })
            # FIXME: update to work with batched requests

            async with httpx.AsyncClient() as http:
                lrclib_client = LrclibClient(http)
                deepl_client = DeepLClient(http)
                result1 = await ingest_track(db_session, lrclib_client, deepl_client, "Обійми", "Okean Elzy")
                track1 = TrackOut.model_validate(result1)
                result2 = await get_track_by_lrclib_id(db_session, 1)
                track2 = TrackOut.model_validate(result2)

    assert result1 is not None
    assert result2 is not None
    assert track1.id == track2.id
    for track in [track1, track2]:
        assert track.track_name == "Обійми"
        assert track.artist_name == "Океан Ельзи"
        assert track.duration == 245
        assert len(track.lines) == 1
        line = track.lines[0]
        assert line.time == 21500
        assert line.text == "Обійми мене"
        assert line.translation == "Embrace me"

        token = line.tokens[0]
        assert token.text == "Обійми"
        assert token.lemma is not None      # not sure what spaCy returns for lemma of this word
        assert token.pos is not None        # not sure what spaCy returns for pos of this word
        assert token.sense == "Embrace me"  # since mock returns same line
