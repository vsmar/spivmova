from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.lrclib import LrclibTrack
from spivmova.db.models import LyricLine, Track
from spivmova.db.repository import get_track_by_lrclib_id, persist_track
from spivmova.nlp.lrc import LyricLine as ParsedLine
from spivmova.clients.lrclib import LrclibClient
from spivmova.services.lyrics import get_lyrics
from spivmova.nlp.lrc import parse_lrc

async def save_track(
        session: AsyncSession, 
        lrclib_track: LrclibTrack, 
        parsed_lines: list[ParsedLine]
) -> Track:
    exists = await get_track_by_lrclib_id(session, lrclib_track.id)
    if exists is not None:
        return exists

    # otherwise create the track
    lines = [
        LyricLine(position=i, time=line.time, text=line.text)
        for i, line in enumerate(parsed_lines)
    ]
        # is this possible as im not declaring the track_id yet?
    
    track = Track(
        lrclib_id=lrclib_track.id,
        track_name=lrclib_track.track_name,
        artist_name=lrclib_track.artist_name,
        album_name=lrclib_track.album_name,
        duration=lrclib_track.duration,
        instrumental=lrclib_track.instrumental,
        lines = lines
    )
    return await persist_track(session, track)


async def ingest_track(
        session: AsyncSession, 
        client: LrclibClient,
        track: str,
        artist: str,
        album: str | None = None,
        duration: float | None = None
) -> Track | None:
    """Ingest a track and its lyrics into the database."""
    lrclib_track = await get_lyrics(client,
                                    track, 
                                    artist, 
                                    album=album, 
                                    duration=duration)

    if lrclib_track is None:
        return None

    if lrclib_track.best_lyrics is None:
        parsed_lines = []
    else:
        parsed_lines = parse_lrc(lrclib_track.best_lyrics)

    return await save_track(session, lrclib_track, parsed_lines)