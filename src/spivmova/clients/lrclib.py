import httpx
from pydantic import BaseModel, Field


class LrclibTrack(BaseModel):
    # model_config = ConfigDict(populate_by_name=True)
    id: int
    track_name: str = Field(alias="trackName") # lrclib returns camelCase
    artist_name: str = Field(alias="artistName")
    album_name: str | None = Field(default=None, alias="albumName")
    duration: float | None = None
    instrumental: bool = False # indicates if no lyrics
    plain_lyrics: str | None = Field(default=None, alias="plainLyrics")
    synced_lyrics: str | None = Field(default=None, alias="syncedLyrics")

    @property
    def best_lyrics(self) -> str | None:
        return self.synced_lyrics or self.plain_lyrics # prefer synced

    @property
    def is_synced(self) -> bool:
        return self.synced_lyrics is not None

class LrclibNotFound(Exception):
    pass

class LrclibClient:
    BASE = "https://lrclib.net/api"

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def get_by_id(self, lrclib_id: int) -> LrclibTrack:
        r = await self._http.get(f"{self.BASE}/get/{lrclib_id}")
        if r.status_code == 404:
            raise LrclibNotFound()
        r.raise_for_status()
        return LrclibTrack.model_validate(r.json())

    async def get_by_meta(
            self, 
            track_name: str,
            artist_name: str,
            album_name: str | None = None,
            duration: float | None = None
    ) -> LrclibTrack:
        params = {"track_name": track_name, "artist_name": artist_name}
        if album_name is not None:
            params["album_name"] = album_name
        if duration is not None:
            params["duration"] = int(duration)
        r = await self._http.get(f"{self.BASE}/get", params=params)

        if r.status_code == 404:
            raise LrclibNotFound(f"{artist_name} - {track_name}")
        r.raise_for_status()
        return LrclibTrack.model_validate(r.json())

    async def search(
            self,
            track_name: str | None = None,
            artist_name: str | None = None,
            album_name: str | None = None,
            q: str | None = None
    ) -> list[LrclibTrack]:
        if q is None and track_name is None:
            raise ValueError("At least one of 'q' or 'track_name' must be provided")

        params = {}
        if q is not None:
            params["q"] = q
        if track_name is not None:
            params["track_name"] = track_name
        if artist_name is not None:
            params["artist_name"] = artist_name
        if album_name is not None:
            params["album_name"] = album_name

        r = await self._http.get(f"{self.BASE}/search", params=params)
        r.raise_for_status()
        return [LrclibTrack.model_validate(track) for track in r.json()]
