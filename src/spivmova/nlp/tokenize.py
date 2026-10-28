import spacy
from pydantic import BaseModel

from spivmova.config import settings

NLP = spacy.load(settings.spacy_model)


class TokenData(BaseModel):
    position: int
    text: str
    lemma: str
    pos: str
    start_char: int
    end_char: int
    translatable: bool


def tokenize_line(text: str) -> list[TokenData]:
    """Tokenize a line of text into words"""
    doc = NLP(text)
    tokens = [
        TokenData(
            position=i,
            text=token.text,
            lemma=token.lemma_,
            pos=token.pos_,
            start_char=token.idx,
            end_char=token.idx + len(token.text),
            translatable=any(c.isalnum() for c in token.text),
        )
        for i, token in enumerate(doc)
        if not token.is_space
    ]  # exclude whitespace tokens

    return tokens
