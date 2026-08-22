# This formatting, does make for a lot of token redundancy
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from spivmova.db.base import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    lrclib_id: Mapped[int | None] = mapped_column(unique=True)
    track_name: Mapped[str]
    artist_name: Mapped[str]
    album_name: Mapped[str | None] = mapped_column(default=None)
    duration: Mapped[float | None] = mapped_column(default=None)
    instrumental: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    lines: Mapped[list["LyricLine"]] = relationship(
        back_populates="track", order_by="LyricLine.position"
    )


class LyricLine(Base):
    __tablename__ = "lyric_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"))
    translation_id: Mapped[int | None] = mapped_column(ForeignKey("line_translations.id"))
    position: Mapped[int]
    time: Mapped[int | None] = mapped_column(default=None)
    text: Mapped[str]

    translation: Mapped["LineTranslation"] = relationship(back_populates="lines")
    track: Mapped["Track"] = relationship(back_populates="lines")
    tokens: Mapped[list["Token"]] = relationship(
        back_populates="line", order_by="Token.position"
    )


class LineTranslation(Base):
    __tablename__ = "line_translations"

    id: Mapped[int] = mapped_column(primary_key=True)
    text_hash: Mapped[str] = mapped_column(unique=True)
    source_text: Mapped[str]
    translation: Mapped[str]
    provider: Mapped[str]
    translated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    lines: Mapped[list["LyricLine"]] = relationship(back_populates="translation")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(primary_key=True)
    lemma: Mapped[str]
    pos: Mapped[str]

    __table_args__ = (
        UniqueConstraint("lemma", "pos"),
    )

    senses: Mapped[list["Sense"]] = relationship(
        back_populates="vocab"
    )
    tokens: Mapped[list["Token"]] = relationship(
        back_populates="vocab"
    )


class Sense(Base):
    __tablename__ = "senses"

    id: Mapped[int] = mapped_column(primary_key=True)
    vocab_id: Mapped[int] = mapped_column(ForeignKey("vocabulary.id"))
    translation: Mapped[str]
    provider: Mapped[str]
    example_line_id: Mapped[int | None] = mapped_column(ForeignKey("lyric_lines.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    vocab: Mapped["Vocabulary"] = relationship(back_populates="senses")
    tokens: Mapped[list["Token"]] = relationship(
        back_populates="sense"
    )


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("lyric_lines.id"))
    position: Mapped[int]
    text: Mapped[str]
    start_char: Mapped[int]
    end_char: Mapped[int]
    vocab_id: Mapped[int | None] = mapped_column(ForeignKey("vocabulary.id"))
    sense_id: Mapped[int | None] = mapped_column(ForeignKey("senses.id"))

    vocab: Mapped["Vocabulary | None"] = relationship(back_populates="tokens")
    sense: Mapped["Sense | None"] = relationship(back_populates="tokens")
    line: Mapped["LyricLine"] = relationship(back_populates="tokens")
