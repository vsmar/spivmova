from pydantic import BaseModel, ConfigDict


class LyricLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    time: int | None
    text: str


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_name: str
    artist_name: str
    album_name: str | None
    duration: float | None
    lines: list[LyricLineOut]