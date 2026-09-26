from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.youtube import YouTubeClient
from spivmova.db.repository import get_track_by_id


class TrackNotFound(Exception):
    pass

async def get_or_search_video_id(
        session: AsyncSession, 
        youtube_client: YouTubeClient,
        track_id: int, 
        manual_id: str | None = None
):
    track = await get_track_by_id(session, track_id)
    if track is None:
        raise TrackNotFound()

    if manual_id:
        track.youtube_video_id = manual_id
        await session.commit()
        return manual_id # TODO: Check that the manual id is valid
    if track.youtube_video_id:
        return track.youtube_video_id
    video_id = await youtube_client.search_video(f"{track.track_name} {track.artist_name}")
    if video_id:
        track.youtube_video_id = video_id
        await session.commit()
    return video_id