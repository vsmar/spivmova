from collections import defaultdict
from collections.abc import KeysView
from dataclasses import dataclass, field
from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.clients.lrclib import LrclibClient, LrclibTrack
from spivmova.clients.translator import (
    ContextualTranslation,
    ContextualTranslator,
    ContextUnit,
    ElementInput,
)
from spivmova.db.models import LineTranslation, LyricLine, Token, Track
from spivmova.db.repository import (
    get_example_lyric_line,
    get_line_translation_by_hash,
    get_or_create_sense,
    get_or_create_vocabulary,
    get_track_by_lrclib_id,
    persist_track,
    text_hash,
)
from spivmova.nlp.lrc import ParsedLine, parse_lrc
from spivmova.nlp.tokenize import TokenData, tokenize_line
from spivmova.services.lyrics import get_lyrics


class HashedLine(ParsedLine):
    @cached_property
    def line_hash(self) -> str:
        return text_hash(self.text)


@dataclass
class TokenizedLine:
    text: str
    tds: list[TokenData] = field(init=False)
    context_unit: ContextUnit | None = field(init=False)

    def __post_init__(self):
        self.tds = [td for td in tokenize_line(self.text) if td.translatable]
        elements = [ElementInput(position=td.position, text=td.text) for td in self.tds]
        self.context_unit = ContextUnit(context=self.text, elements=elements) if elements else None

    def translatable(self) -> bool:
        return self.context_unit is not None


def build_ll(track: Track, parsed_line: ParsedLine, **refs):
    return LyricLine(
        track=track,
        position=parsed_line.position,
        time=parsed_line.time,
        text=parsed_line.text,
        **refs,
    )


def build_token(src: TokenData | Token, line: LyricLine, **refs):
    return Token(
        position=src.position,
        text=src.text,
        start_char=src.start_char,
        end_char=src.end_char,
        line=line,
        **refs,
    )


async def get_unique_lines(
    session: AsyncSession, hash_keys: KeysView[str]
) -> tuple[list[str], dict[str, LyricLine]]:
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
            if example_lyric_line is None:
                raise ValueError(
                    f"LineTranslation with hash {hash_key} exists but has no associated LyricLine"
                )  # NOTE: This can be handled more gracefully
            existing[hash_key] = example_lyric_line
    return (translate_hashes, existing)


async def store_new_lines(
    session: AsyncSession,
    track: Track,
    hash_str: str,
    parsed_lines: list[ParsedLine],  # timing
    tokenized: TokenizedLine,  # tokens
    translated: ContextualTranslation,  # translation
):
    translation = LineTranslation(
        text_hash=hash_str,
        source_text=translated.context.source,
        translation=translated.context.translation,
        provider=translated.provider,
    )
    session.add(translation)

    n_lines = len(parsed_lines)

    lyriclines = [
        build_ll(track=track, parsed_line=p, translation=translation) for p in parsed_lines
    ]
    session.add_all(lyriclines)

    by_pos = {el.position: el for el in translated.elements}
    for td in tokenized.tds:
        vocab = await get_or_create_vocabulary(session, td.lemma, td.pos)
        sense = await get_or_create_sense(
            session,
            vocab=vocab,
            translation=by_pos[td.position].translation,
            provider=translated.provider,
            lyric_line=lyriclines[0],
            # TODO: Examine if we want to keep this example line mapping
        )

        tokens = [
            build_token(
                src=td,
                line=lyriclines[i],
                vocab=vocab,
                sense=sense,
                # TODO: add parsedline char matching for word timing
            )
            for i in range(n_lines)
        ]

        session.add_all(tokens)


async def clone_line_translation(
    session: AsyncSession,
    track: Track,
    parsed_lines: list[ParsedLine],
    og_line: LyricLine,
):
    n_lines = len(parsed_lines)

    cloned_lines = [
        build_ll(track=track, parsed_line=p, translation_id=og_line.translation_id)
        for p in parsed_lines
    ]
    session.add_all(cloned_lines)

    new_tokens = []
    for i in range(n_lines):
        new_tokens.extend(
            [
                build_token(
                    src=token,
                    line=cloned_lines[i],
                    vocab_id=token.vocab_id,
                    sense_id=token.sense_id,
                    # TODO: add parsedline char matching for word timing
                )
                for token in og_line.tokens
            ]
        )
    session.add_all(new_tokens)


async def save_track(
    session: AsyncSession,
    translator: ContextualTranslator,
    lrclib_track: LrclibTrack,
) -> Track:
    # Create a new track instance
    track = Track(
        lrclib_id=lrclib_track.id,
        track_name=lrclib_track.track_name,
        artist_name=lrclib_track.artist_name,
        album_name=lrclib_track.album_name,
        duration=lrclib_track.duration,
        instrumental=lrclib_track.instrumental,
    )
    session.add(track)

    # Parse track lyrics
    all_parsed_lines = (
        [] if lrclib_track.best_lyrics is None else parse_lrc(lrclib_track.best_lyrics)
    )

    # Filter out lines without text
    parsed_lines = []
    for p in all_parsed_lines:
        if not p.text:
            session.add(build_ll(track, p))
        else:
            parsed_lines.append(p)

    # Set up map for dedup
    hash_to_line = defaultdict(list)
    for p in parsed_lines:
        hash_to_line[text_hash(p.text)].append(p)

    # Identify what text needs new translation
    # NOTE: currently context stops at the line level
    translate_hashes, existing_ll = await get_unique_lines(session, hash_to_line.keys())

    # Clone any already existing lls
    for h, example_ll in existing_ll.items():
        await clone_line_translation(session, track, hash_to_line[h], example_ll)

    # Tokenize new lines
    tokenized = {h: TokenizedLine(text=hash_to_line[h][0].text) for h in translate_hashes}

    to_translate = {}
    for h, tl in tokenized.items():
        if tl.translatable():
            to_translate[h] = tl
        else:
            # Skip translation for lines that aren't translatable
            session.add_all([build_ll(track, p) for p in hash_to_line[h]])

    if to_translate:
        translated_units = await translator.contextual_batch_translate(
            context_units=[tl.context_unit for tl in to_translate.values()],
            # TODO: Add source language detection?
        )

        # Store new lines (tokens, vocab, senses)
        for (h, tl), translated in zip(to_translate.items(), translated_units, strict=True):
            await store_new_lines(session, track, h, hash_to_line[h], tl, translated)

    await persist_track(session, track)
    # re-fetch through the same eager-loaded query as the "already exists" path,
    # so the return value is always fully loaded regardless of which branch ran
    return await get_track_by_lrclib_id(session, lrclib_track.id)


async def ingest_track(
    session: AsyncSession,
    lrc_client: LrclibClient,
    translator: ContextualTranslator,
    track: str,
    artist: str,
    album: str | None = None,
    duration: float | None = None,
) -> Track | None:
    """Ingest a track and its lyrics into the database."""
    lrclib_track = await get_lyrics(lrc_client, track, artist, album=album, duration=duration)
    if lrclib_track is None:
        return None

    # Check if track already exists in db
    existing = await get_track_by_lrclib_id(session, lrclib_track.id)
    if existing is not None:
        return existing

    # Ingest, save and load the track
    return await save_track(session, translator, lrclib_track)
