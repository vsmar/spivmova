from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spivmova.db.models import Track


async def get_track_by_lrclib_id(
        session: AsyncSession, 
        lrclib_id: int
) -> Track | None:
    stmt = select(Track).where(Track.lrclib_id == lrclib_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def persist_track(
        session: AsyncSession, 
        track: Track
) -> Track:
    session.add(track)
    await session.commit()
    return track
