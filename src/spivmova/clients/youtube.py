import httpx
from pydantic import BaseModel, Field

from spivmova.config import settings


class YouTubeClient:
    DATA_BASE = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def search_video(self, query: str) -> str | None:
        params = {
            "part": "id,snippet",
            "q": query,
            "type": "video",
            "maxResults": 1, # TODO: improve picking (duration based? already done with lrclib querying)
            "key": settings.youtube_api_key,
        }
        r = await self._http.get(self.DATA_BASE, params=params)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if not items:
            return None
        video_id = items[0]["id"]["videoId"]
        return video_id

    # # TODO: Add method to check video details
    # async def get_video_details(self, video_id: str) -> dict | None:
    #     params = {
    #         "part": "snippet,contentDetails",
    #         "id": video_id,
    #         "key": settings.youtube_api_key,
    #     }
    #     r = await self._http.get(self.DATA_BASE, params=params)
    #     r.raise_for_status()
    #     data = r.json()
    #     items = data.get("items", [])
    #     if not items:
    #         return None
    #     return items[0]