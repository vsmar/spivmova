from fastapi import APIRouter, HTTPException

from spivmova.api.deps import DbSession, Deepl, Lrclib
from spivmova.api.schemas import TrackOut
from spivmova.services.ingestion import ingest_track

router = APIRouter()

@router.get("/tracks/search", response_model=TrackOut)
async def search_track(
    session: DbSession,
    lrc_client: Lrclib,
    translation_client: Deepl,
    track: str,
    artist: str,
    album: str | None = None,
    duration: float | None = None,
):
    result = await ingest_track(
        session,
        lrc_client,
        translation_client,
        track=track,
        artist=artist,
        album=album,
        duration=duration,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return TrackOut.model_validate(result)

