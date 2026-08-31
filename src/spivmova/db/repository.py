from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spivmova.db.models import Track, Vocabulary


async def get_track_by_lrclib_id(
        session: AsyncSession, 
        lrclib_id: int
) -> Track | None:
    stmt = (
        select(Track)
        .where(Track.lrclib_id == lrclib_id)
        .options(selectinload(Track.lines)) # eager load lines
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def persist_track(
        session: AsyncSession, 
        track: Track
) -> Track:
    session.add(track)
    await session.commit()
    return track


async def get_or_create_vocabulary(
        session: AsyncSession, 
        lemma: str, 
        pos: str
) -> Vocabulary:
    stmt = select(Vocabulary).where(Vocabulary.lemma == lemma, Vocabulary.pos == pos)
    result = await session.execute(stmt)
    vocab = result.scalar_one_or_none()
    if vocab is None:
        vocab = Vocabulary(lemma=lemma, pos=pos)
        session.add(vocab)
    return vocab

