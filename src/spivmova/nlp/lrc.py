import re

from pydantic import BaseModel

# Cyrillic is included by default in \w for Python 3 regex
# Line timing: [00:21.50]
LINETIME_RE = re.compile(r"\[(\d{2}):(\d{2})[.:](\d{2,3})\]")

# Word Timing (ELRC): <00:21.50>
WORDTIME_RE = re.compile(r"\<(\d{2}):(\d{2})[.:](\d{2,3})\>")

# Meta [tag name (2+ roman letters) : str]
META_RE = re.compile(r"\[([a-z]{2,}):(.*)\]", re.IGNORECASE)

class WordTiming(BaseModel):
    word: str
    time: float


class LyricLine(BaseModel):
    text: str
    time: float | None = None
    words: list[WordTiming] = []


def _to_ms(mm: str, ss: str, frac:str) -> int:
    return int(mm)*60000 + int(ss)*1000 + int(frac.ljust(3, "0"))


def _parse_words(raw: str) -> list[WordTiming]:
    """Extract <mm:ss:xx> + word pairs from an enhanced-LRC line body."""
    words = []
    matches = list(WORDTIME_RE.finditer(raw))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i+1 < len(matches) else len(raw)
        word = raw[match.end():end].strip()
        if word:
            words.append(WordTiming(word=word, time=_to_ms(*match.groups())))
    return words


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    lines: list[LyricLine] = []

    for raw in lrc_text.splitlines():
        stamps = list(LINETIME_RE.finditer(raw))

        if not stamps and META_RE.match(raw): 
            # extra protection against times being interpreted as lyrics
            continue

        body = LINETIME_RE.sub("", raw)
        words = _parse_words(body)
        text = WORDTIME_RE.sub("", body)

        if not text:
            continue

        if not stamps:
            lines.append(LyricLine(text=text))

        for m in stamps:
            lines.append(LyricLine(text=text, time=_to_ms(*m.groups()), words=words))

    if all(line.time is not None for line in lines):
        lines.sort(key=lambda line: line.time)
    return lines