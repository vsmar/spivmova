import httpx
import respx

from spivmova.clients.lrclib import LrclibClient
from spivmova.services.ingestion import ingest_track


async def test_ingest_track_with_single_song(db_session):
    with respx.mock(base_url="https://lrclib.net/api") as mock:
        mock.get("/get").respond(404)
        mock.get("/search").respond(200, json=[
            {"id": 1, "trackName": "Обійми", "artistName": "Океан Ельзи",
             "duration": 245, "syncedLyrics": "[00:21.50] Обійми мене"},
        ])

        async with httpx.AsyncClient() as http:
            client = LrclibClient(http)
            result = await ingest_track(db_session, client, "Обійми", "Okean Elzy")
            # idempotency test
            result2 = await ingest_track(db_session, client, "Обійми", "Okean Elzy")

    assert result is not None
    assert result.lrclib_id == 1
    assert result2 is not None
    assert result.id == result2.id