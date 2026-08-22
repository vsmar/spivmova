from spivmova.clients.lrclib import LrclibClient, LrclibNotFound, LrclibTrack


async def get_lyrics(
        client: LrclibClient,
        track: str,
        artist: str,
        album: str | None = None,
        duration: float | None = None
    ) -> LrclibTrack | None:
    try:
        return await client.get_by_meta(track, artist, 
                                        album_name=album, duration=duration)
    except LrclibNotFound:
        pass

    hits = await client.search(track_name=track, artist_name=artist)
    if not hits:
        return None

    return pick_best(hits, duration=duration)

def pick_best(hits: list[LrclibTrack], duration: float | None = None) -> LrclibTrack | None:
    # Prefer synced, non-instrumental, with closest matching duration
    def penalty(track: LrclibTrack) -> tuple[int, int, float]:
        synced = int(not track.is_synced)
        gap = (abs(track.duration - duration) 
                if duration is not None and track.duration is not None 
                else float("inf")
            )
        return (synced, int(track.instrumental), gap)

    return min(hits, key=penalty) if hits else None