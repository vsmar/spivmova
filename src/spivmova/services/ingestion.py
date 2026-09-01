from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient, LrclibTrack
from spivmova.db.models import LineTranslation, LyricLine, Token, Track
from spivmova.db.repository import (
    get_line_translation_by_hash,
    get_or_create_sense,
    get_or_create_vocabulary,
    get_sense_for_line_translation,
    get_track_by_lrclib_id,
    persist_track,
    text_hash,
)
from spivmova.nlp.lrc import LyricLine as ParsedLine
from spivmova.nlp.lrc import parse_lrc
from spivmova.nlp.tokenize import tokenize_line
from spivmova.services.lyrics import get_lyrics


async def translate_line(
    session: AsyncSession, translation_client: DeepLClient, text: str
) -> tuple[LineTranslation, bool]:
    hash_str = text_hash(text)
    translation = await get_line_translation_by_hash(session, hash_str)
    if translation is None:
        # NOTE: support other translation APIs (google)?
        response = await translation_client.translate(text=text, target_lang="EN-US")
        translation = LineTranslation(
            text_hash=hash_str,
            source_text=text,
            translation=response.translated_text,
            provider="deepl",
        )
        session.add(translation)
        is_new = True
    else:
        is_new = False
    return (translation, is_new)


# async def translate_token(
#     session: AsyncSession,
#     translation_client: DeepLClient,
#     text: str
# ) ->


async def save_track(
    session: AsyncSession,
    translation_client: DeepLClient,
    lrclib_track: LrclibTrack,
    parsed_lines: list[ParsedLine],
) -> Track:
    existing = await get_track_by_lrclib_id(session, lrclib_track.id)
    if existing is not None:
        return existing

    track = Track(
        lrclib_id=lrclib_track.id,
        track_name=lrclib_track.track_name,
        artist_name=lrclib_track.artist_name,
        album_name=lrclib_track.album_name,
        duration=lrclib_track.duration,
        instrumental=lrclib_track.instrumental,
    )
    session.add(track)

    # otherwise create the track
    for i, line in enumerate(parsed_lines):
        translation = await translate_line(session, translation_client, line.text)
        lyricline = LyricLine(
            track=track, position=i, time=line.time, text=line.text, translation=translation[0]
        )
        session.add(lyricline)

        for j, td in enumerate(tokenize_line(line.text)):
            if td.pos != "PUNCT":
                vocab = await get_or_create_vocabulary(session, td.lemma, td.pos)

                if translation[1]:  # check if new lyric
                    response = await translation_client.translate(
                        text=td.text, target_lang="EN-US", context=line.text
                    )
                    sense = await get_or_create_sense(
                        session,
                        vocab=vocab,
                        translation=response.translated_text,
                        provider="deepl",
                        lyric_line=lyricline,
                    )
                else:
                    sense = await get_sense_for_line_translation(
                        session,
                        translation_id=translation[0].id,
                        vocab_id=vocab.id,
                    )
            else:
                vocab = None
                sense = None
            session.add(
                Token(
                    position=j,
                    text=td.text,
                    start_char=td.start_char,
                    end_char=td.end_char,
                    vocab=vocab,
                    sense=sense,
                    line=lyricline,
                )
            )

    return await persist_track(session, track)


async def ingest_track(
    session: AsyncSession,
    lrc_client: LrclibClient,
    translation_client: DeepLClient,
    track: str,
    artist: str,
    album: str | None = None,
    duration: float | None = None,
) -> Track | None:
    """Ingest a track and its lyrics into the database."""
    lrclib_track = await get_lyrics(lrc_client, track, artist, album=album, duration=duration)

    if lrclib_track is None:
        return None

    if lrclib_track.best_lyrics is None:
        parsed_lines = []
    else:
        parsed_lines = parse_lrc(lrclib_track.best_lyrics)

    return await save_track(session, translation_client, lrclib_track, parsed_lines)
