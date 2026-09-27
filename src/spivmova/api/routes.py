from fastapi import APIRouter, HTTPException

from spivmova.api.deps import DbSession, Deepl, Lrclib, YouTube
from spivmova.api.schemas import TrackOut, VideoOut, VideoOverrideIn
from spivmova.clients.deepl import DeepLError
from spivmova.services.ingestion import ingest_track
from spivmova.services.player import TrackNotFound, get_or_search_video_id

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
    try:
        result = await ingest_track(
            session,
            lrc_client,
            translation_client,
            track=track,
            artist=artist,
            album=album,
            duration=duration,
        )
    except DeepLError as e:
         raise HTTPException(
            status_code=502, 
            detail=f"Translation failed: {e.message}"
        ) from e
    
    if result is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return TrackOut.model_validate(result)


@router.get("/tracks/{track_id}/video", response_model=VideoOut)
async def get_track_video(
    session: DbSession,
    youtube_client: YouTube,
    track_id: int
):
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
            video_id = await get_or_search_video_id(session, youtube_client, track_id, body.youtube_video_id)
        except TrackNotFound as e:
            raise HTTPException(status_code=404, detail="Track is missing") from e
        return VideoOut(youtube_video_id=video_id)
