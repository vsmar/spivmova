import httpx
from pydantic import BaseModel, Field


class LrclibTrack(BaseModel):
    id: int
    track_name: str = Field(alias="trackName")  # lrclib returns camelCase
    artist_name: str = Field(alias="artistName")
    album_name: str | None = Field(default=None, alias="albumName")
    duration: float | None = None
    instrumental: bool = False  # indicates if no lyrics
    plain_lyrics: str | None = Field(default=None, alias="plainLyrics")
    synced_lyrics: str | None = Field(default=None, alias="syncedLyrics")

    @property
    def best_lyrics(self) -> str | None:
        return self.synced_lyrics or self.plain_lyrics  # prefer synced

    @property
    def is_synced(self) -> bool:
        return self.synced_lyrics is not None


class LrclibNotFound(Exception):
    pass


class LrclibError(Exception):
    def __init__(self, status_code: int | None, message: str, retry_after: float | None = None):
        super().__init__(f"Lrclib {status_code}: {message}")
        self.status_code = status_code
        self.message = message
        self.retry_after = retry_after


def _error_from(r: httpx.Response) -> LrclibError:
    try:
        body = r.json()
        message = body.get("message") if isinstance(body, dict) else None
    except ValueError:
        message = None
    return LrclibError(r.status_code, message or r.text[:200])


class LrclibClient:
    BASE = "https://lrclib.net/api"

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        try:
            r = await self._http.get(f"{self.BASE}{path}", params=params)
        except httpx.RequestError as e:
            raise LrclibError(None, f"Unreachable: {e}") from e
        if r.status_code == 404:
            raise LrclibNotFound(f"{path} {params or ''} not found")
        if not r.is_success:
            raise _error_from(r)
        return r

    # async def get_by_id(self, lrclib_id: int) -> LrclibTrack:
    #     r = await self._get(f"{self.BASE}/get/{lrclib_id}")
    #     return LrclibTrack.model_validate(r.json())

    async def get_by_meta(
        self,
        track_name: str,
        artist_name: str,
        album_name: str | None = None,
        duration: float | None = None,
    ) -> LrclibTrack:
        params = {"track_name": track_name, "artist_name": artist_name}
        if album_name is not None:
            params["album_name"] = album_name
        if duration is not None:
            params["duration"] = int(duration)
        r = await self._get("/get", params=params)
        return LrclibTrack.model_validate(r.json())

    async def search(
        self,
        track_name: str | None = None,
        artist_name: str | None = None,
        album_name: str | None = None,
        q: str | None = None,
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

        r = await self._get("/search", params=params)
        return [LrclibTrack.model_validate(track) for track in r.json()]
