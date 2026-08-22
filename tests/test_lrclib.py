import httpx
import respx

from spivmova.clients.lrclib import LrclibClient
from spivmova.services.lyrics import get_lyrics


async def test_falls_back_to_search_on_404():
    with respx.mock(base_url="https://lrclib.net/api") as mock:
        mock.get("/get").respond(404)
        mock.get("/search").respond(200, json=[
            {"id": 1, "trackName": "Обійми", "artistName": "Океан Ельзи",
             "duration": 245, "syncedLyrics": "[00:21.50] Обійми мене"},
        ]) # TODO: add another track
        async with httpx.AsyncClient() as http:
            client = LrclibClient(http)
            result = await get_lyrics(client, "Обійми", "Okean Elzy")

    assert result is not None
    assert result.id == 1
    assert result.is_synced