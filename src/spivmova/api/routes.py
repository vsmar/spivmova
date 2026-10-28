import logging
import unicodedata

from fastapi import APIRouter, HTTPException

from spivmova.api.deps import DbSession, Lrclib, Translator, YouTube
from spivmova.api.schemas import TrackOut, VideoOut, VideoOverrideIn
from spivmova.clients.lrclib import LrclibError
from spivmova.clients.translator import TranslationError
from spivmova.services.ingestion import ingest_track
from spivmova.services.player import TrackNotFound, get_or_search_video_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tracks/search", response_model=TrackOut)
async def search_track(
    session: DbSession,
    lrc_client: Lrclib,
    translator: Translator,
    track: str,
    artist: str,
    album: str | None = None,
    duration: float | None = None,
):
    # NOTE: normalization to NFC may not be necessary
    track = unicodedata.normalize("NFC", track)
    artist = unicodedata.normalize("NFC", artist)
    album = unicodedata.normalize("NFC", album) if album is not None else None

    try:
        result = await ingest_track(
            session,
            lrc_client,
            translator,
            track=track,
            artist=artist,
            album=album,
            duration=duration,
        )
    except LrclibError as e:
        logger.warning("lrclib %s: %s", e.status_code, e.message)
        if e.status_code is None or e.status_code >= 500:
            raise HTTPException(
                status_code=503, detail="Lyrics service is unavailable, try again later"
            ) from e
        raise HTTPException(status_code=502, detail=f"Lyrics lookup failed: {e.message}") from e
    except TranslationError as e:
        logger.warning("translation failed (retryable=%s): %s", e.retryable, e.message)
        if e.retryable:
            raise HTTPException(503, "Translation service is unavailable, try again later") from e
        raise HTTPException(502, f"Translation failed: {e.message}") from e

    if result is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return TrackOut.model_validate(result)


@router.get("/tracks/{track_id}/video", response_model=VideoOut)
async def get_track_video(session: DbSession, youtube_client: YouTube, track_id: int):
    try:
        video_id = await get_or_search_video_id(session, youtube_client, track_id)
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail="Track is missing") from e
    return VideoOut(youtube_video_id=video_id)


@router.put("/tracks/{track_id}/video", response_model=VideoOut)
async def set_track_video(
    session: DbSession,
    youtube_client: YouTube,
    track_id: int,
    body: VideoOverrideIn,
):
    try:
        video_id = await get_or_search_video_id(
            session, youtube_client, track_id, body.youtube_video_id
        )
    except TrackNotFound as e:
        raise HTTPException(status_code=404, detail="Track is missing") from e
    return VideoOut(youtube_video_id=video_id)
