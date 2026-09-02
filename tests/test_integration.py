import httpx
import pytest

from spivmova.api.routes import search_track
from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient

TRACK = "Без бою"
ARTIST = "Okean Elzy"
LRCLIB_ID = 3109221


@pytest.mark.integration
async def test_ingest_track_with_single_song(db_session):
    async with httpx.AsyncClient() as http:
        lrclib_client = LrclibClient(http)
        deepl_client = DeepLClient(http)
        try:
            result = await search_track(
                session=db_session,
                lrc_client=lrclib_client,
                translation_client=deepl_client,
                track=TRACK,
                artist=ARTIST,
            )
        except Exception as e:
            pytest.fail(f"search_track raised an exception: {e}")

    assert result.track_name == "Без бою"
    assert result.artist_name == "Okean Elzy"  # NOTE: might be too aggressive
    assert result.lines is not None
    line0 = result.lines[0]
    assert line0.position >= 0
    assert line0.tokens is not None
    token0 = line0.tokens[0]
    assert token0.text is not None
    assert token0.lemma is not None
    assert token0.pos is not None
    assert token0.sense is not None

    print(
        f"Track {result.track_name} by {result.artist_name} "
        f"ingested successfully with {len(result.lines)} lines."
    )
    for line in result.lines[:10]:
        print(f"  line {line.position}: {line.text!r} -> {line.translation!r}")

    all_tokens = [tok for line in result.lines for tok in line.tokens]
    for tok in all_tokens[:5]:
        print(f"  token {tok.text!r}: lemma={tok.lemma}, pos={tok.pos}, sense={tok.sense!r}")
