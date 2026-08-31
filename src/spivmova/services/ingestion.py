from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.lrclib import LrclibClient, LrclibTrack
from spivmova.db.models import LyricLine, Token, Track
from spivmova.db.repository import get_or_create_vocabulary, get_track_by_lrclib_id, persist_track
from spivmova.nlp.lrc import LyricLine as ParsedLine
from spivmova.nlp.lrc import parse_lrc
from spivmova.nlp.tokenize import tokenize_line
from spivmova.services.lyrics import get_lyrics


async def save_track(
    session: AsyncSession, lrclib_track: LrclibTrack, parsed_lines: list[ParsedLine]
) -> Track:
    existing = await get_track_by_lrclib_id(session, lrclib_track.id)
    if existing is not None:
        return existing

    # otherwise create the track
    with session.no_autoflush:
        lines = []
        for i, line in enumerate(parsed_lines):
            tokens = []
            for j, td in enumerate(tokenize_line(line.text)):
                if td.pos != "PUNCT":
                    vocab = await get_or_create_vocabulary(session, td.lemma, td.pos)
                else:
                    vocab = None
                tokens.append(
                    Token(
                        position=j,
                        text=td.text,
                        start_char=td.start_char,
                        end_char=td.end_char,
                        vocab=vocab,
                    )
                )
            lines.append(LyricLine(position=i, time=line.time, text=line.text, tokens=tokens))

    track = Track(
        lrclib_id=lrclib_track.id,
        track_name=lrclib_track.track_name,
        artist_name=lrclib_track.artist_name,
        album_name=lrclib_track.album_name,
        duration=lrclib_track.duration,
        instrumental=lrclib_track.instrumental,
        lines=lines,
    )
    return await persist_track(session, track)


async def ingest_track(
    session: AsyncSession,
    client: LrclibClient,
    track: str,
    artist: str,
    album: str | None = None,
    duration: float | None = None,
) -> Track | None:
    """Ingest a track and its lyrics into the database."""
    lrclib_track = await get_lyrics(client, track, artist, album=album, duration=duration)

    if lrclib_track is None:
        return None

    if lrclib_track.best_lyrics is None:
        parsed_lines = []
    else:
        parsed_lines = parse_lrc(lrclib_track.best_lyrics)

    return await save_track(session, lrclib_track, parsed_lines)
