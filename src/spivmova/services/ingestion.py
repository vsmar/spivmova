from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.deepl import DeepLClient
from spivmova.clients.lrclib import LrclibClient, LrclibTrack
from spivmova.db.models import LineTranslation, LyricLine, Token, Track
from spivmova.db.repository import (
    get_line_translation_by_hash,
    get_example_lyric_line,
    get_or_create_sense,
    get_or_create_vocabulary,
    get_track_by_lrclib_id,
    persist_track,
    text_hash,
)
from spivmova.nlp.lrc import LyricLine as ParsedLine
from spivmova.nlp.lrc import parse_lrc
from spivmova.nlp.tokenize import tokenize_line
from spivmova.services.lyrics import get_lyrics


async def get_unique_lines(
    session: AsyncSession, hash_keys: list[str]
) -> tuple[list[str], dict[str, tuple[LyricLine, list[Token]]]]:
    """
    Identify never before seen lines by their hash.
    """
    translate_hashes = []
    existing = {}

    # Check if translation already exists
    for hash_key in hash_keys:
        translation = await get_line_translation_by_hash(session, hash_key)
        if translation is None:
            translate_hashes.append(hash_key)
        else:
            example_lyric_line = await get_example_lyric_line(session, translation.id)
            existing[hash_key] = (example_lyric_line, example_lyric_line.tokens)
    return (translate_hashes, existing)


async def translate_novel_lines(
    session: AsyncSession, 
    translation_client: DeepLClient, 
    translate_hashes: list[str], 
    hash_to_text: dict[str, str]
) -> dict[str, LineTranslation]:
    """ Handles all new line translations (batched call)
    """
    to_translate = [hash_to_text[hash_key] for hash_key in translate_hashes]
    response = await translation_client.translate_batch(
        texts=to_translate, target_lang="EN-US", source_lang="UK"
    )

    hash_to_translated = {}

    # add newly translated lines to map
    for i, hash_key in enumerate(translate_hashes):
        translation = LineTranslation(
            text_hash=hash_key,
            source_text=hash_to_text[hash_key],
            translation=response[i].translated_text,
            provider="deepl",
        )
        session.add(translation)
        hash_to_translated[hash_key] = translation

    return hash_to_translated


async def add_novel_lines(
    session: AsyncSession,
    hash_to_translated: dict[str, LineTranslation],
    ordered_hashes: list[str],
    ordered_text: list[str],
    ordered_time: list[int],
    track: Track
) -> tuple[dict[str, LyricLine], list[int]]:
    """ 
    Adds first occurence of all new lines to the database 
    """
    hash_to_lyricline = {}
    loaded_slots = []
    for hash_key in hash_to_translated.keys():
        position = next(i for i, x in enumerate(ordered_hashes) if x == hash_key)
        lyricline = LyricLine(
            track=track,
            position=position,
            time=ordered_time[position],
            text=ordered_text[position],
            translation=hash_to_translated[hash_key]
        )
        session.add(lyricline)
        loaded_slots.append(position)
        hash_to_lyricline[hash_key] = lyricline

    return (hash_to_lyricline, loaded_slots)


async def tokenize_new_lines(
    session: AsyncSession,
    translation_client: DeepLClient, 
    translate_hashes: list[str],
    hash_to_lyricline: dict[str, LyricLine]
) -> dict[str, tuple[LyricLine, list[Token]]]:
    """ 
    Tokenizes, translates and creates vocab and sense for all new lines
    """
    hash_to_lls_tokens = {}
    for hash_key in translate_hashes:
        lyricline = hash_to_lyricline[hash_key]
        text = lyricline.text
        tds = tokenize_line(text)

        # translate
        response = await translation_client.translate_batch(
            texts=[td.text for td in tds if td.pos != "PUNCT"], 
            target_lang="EN-US", 
            source_lang="UK"
        )

        r_idx = 0
        tokens = []
        for i, td in enumerate(tds):
            if td.pos != "PUNCT":
                vocab = await get_or_create_vocabulary(session, td.lemma, td.pos)
                sense = await get_or_create_sense(
                    session,
                    vocab=vocab,
                    translation=response[r_idx].translated_text,
                    provider="deepl",
                    lyric_line=lyricline
                )
                r_idx += 1

                token = Token(
                    position=i,
                    text=td.text,
                    start_char=td.start_char,
                    end_char=td.end_char,
                    vocab=vocab,
                    sense=sense,
                    line=lyricline,
                )

            else:
                token = Token(
                    position=i,
                    text=td.text,
                    start_char=td.start_char,
                    end_char=td.end_char,
                    line=lyricline,
                )
            session.add(token)
            tokens.append(token)
        hash_to_lls_tokens[hash_key] = (lyricline, tokens)
    return hash_to_lls_tokens


async def clone_non_unique_lines(
    session: AsyncSession,
    track: Track,
    hash_to_lls_tokens: dict[str, tuple[LyricLine, list[Token]]],
    ordered_hash: list[str],
    ordered_time: list[int],
    loaded_slots: list[int]
):
    for i, hash_key in enumerate(ordered_hash):
        if i in loaded_slots:
            continue
        lyricline, tokens = hash_to_lls_tokens[hash_key]

        new_tokens = [
            Token(
                position=token.position,
                text=token.text,
                start_char=token.start_char,
                end_char=token.end_char,
                vocab=token.vocab,
                sense=token.sense,
            ) for token in tokens
        ]
        for cloned_token in new_tokens:
            session.add(cloned_token) # currently not necessary

        cloned_line = LyricLine(
            track=track,
            position=i,
            time=ordered_time[i],
            text=lyricline.text,
            translation=lyricline.translation,
            tokens=new_tokens
        )
        session.add(cloned_line)


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

    lines_text = [line.text for line in parsed_lines]
    ordered_hashes = [text_hash(line) for line in lines_text]
    hash_to_text = dict(zip(ordered_hashes, lines_text, strict=True))

    translate_hashes, pre_existing = await get_unique_lines(session, hash_to_text.keys())

    hash_to_translation = await translate_novel_lines(
        session, translation_client, translate_hashes, hash_to_text
    )

    lines_time = [line.time for line in parsed_lines]
    hash_to_lyriclines, loaded_slots = await add_novel_lines(
        session, hash_to_translation, ordered_hashes, lines_text, lines_time, track
    )


    hash_to_lls_tokens = await tokenize_new_lines(
        session, translation_client, translate_hashes, hash_to_lyriclines
    )

    # Get any relevant pre existing lines
    hash_to_lls_tokens.update(pre_existing)

    await clone_non_unique_lines(
        session, track, hash_to_lls_tokens, ordered_hashes, lines_time, loaded_slots
    )

    await persist_track(session, track)
    # re-fetch through the same eager-loaded query as the "already exists" path,
    # so the return value is always fully loaded regardless of which branch ran
    return await get_track_by_lrclib_id(session, lrclib_track.id)


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
