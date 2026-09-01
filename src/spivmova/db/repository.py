import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spivmova.db.models import LineTranslation, LyricLine, Sense, Token, Track, Vocabulary


async def get_track_by_lrclib_id(session: AsyncSession, lrclib_id: int) -> Track | None:
    stmt = (
        select(Track)
        .where(Track.lrclib_id == lrclib_id)
        .options(selectinload(Track.lines))  # eager load lines
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def persist_track(session: AsyncSession, track: Track) -> Track:
    await session.commit()
    return track


async def get_or_create_vocabulary(session: AsyncSession, lemma: str, pos: str) -> Vocabulary:
    stmt = select(Vocabulary).where(Vocabulary.lemma == lemma, Vocabulary.pos == pos)
    result = await session.execute(stmt)
    vocab = result.scalar_one_or_none()
    if vocab is None:
        vocab = Vocabulary(lemma=lemma, pos=pos)
        session.add(vocab)
    return vocab


def text_hash(text: str) -> int:
    return hashlib.sha256(text.encode()).hexdigest()


async def get_line_translation_by_hash(
    session: AsyncSession, text_hash: str
) -> LineTranslation | None:
    stmt = select(LineTranslation).where(LineTranslation.text_hash == text_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_sense(
    session: AsyncSession, vocab: Vocabulary, translation: str, provider: str, lyric_line: LyricLine
) -> Sense:
    stmt = select(Sense).where(Sense.vocab_id == vocab.id, Sense.translation == translation)
    result = await session.execute(stmt)
    sense = result.scalar_one_or_none()
    if sense is None:
        sense = Sense(
            vocab=vocab, translation=translation, provider=provider, example_line=lyric_line
        )
        session.add(sense)
    return sense


# NOTE: This won't scale well with data
async def get_sense_for_line_translation(
    session: AsyncSession,
    translation_id: LineTranslation,
    vocab_id: Vocabulary,
) -> Sense | None:
    stmt = (
        select(Sense)
        .join(Token, Token.sense_id == Sense.id)
        .join(LyricLine, Token.line_id == LyricLine.id)
        .where(LyricLine.translation_id == translation_id, Token.vocab_id == vocab_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
