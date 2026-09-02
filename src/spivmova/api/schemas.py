from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LyricLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    time: int | None
    text: str
    translation: str | None
    tokens: list["TokenOut"]

    @field_validator("translation", mode="before")
    @classmethod
    def unwrap_translation(cls, value):
        return value.translation if value is not None else None


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    track_name: str
    artist_name: str
    album_name: str | None
    duration: float | None
    lines: list[LyricLineOut]


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    text: str
    start_char: int
    end_char: int
    vocab_id: int | None  # NOTE: To use in future sense list lookup
    lemma: str | None  # token.vocab.lemma
    pos: str | None  # token.vocab.pos
    sense: str | None  # token.sense.translation

    @model_validator(mode="before")
    @classmethod
    def validate_vocab(cls, token):
        return {
            **{
                v: getattr(token, v)
                for v in ["position", "text", "start_char", "end_char", "vocab_id"]
            },
            "lemma": token.vocab.lemma if token.vocab else None,
            "pos": token.vocab.pos if token.vocab else None,
            "sense": token.sense.translation if token.sense else None,
        }


# NOTE: Possible future extension to the API
class SenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    translation: str
    provider: str
    example_line_id: int  # token.sense.example_line.id


class VocabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lemma: str
    pos: str
    senses: list[SenseOut]
