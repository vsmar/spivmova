import spacy
from pydantic import BaseModel

from spivmova.config import settings

NLP = spacy.load(settings.spacy_model)

class TokenData(BaseModel):
    text: str
    lemma: str
    pos: str
    start_char: int
    end_char: int


def tokenize_line(text: str) -> list[TokenData]:
    """ Tokenize a line of text into words"""
    doc = NLP(text)
    tokens = [
        TokenData(
            text=token.text,
            lemma=token.lemma_,
            pos=token.pos_,
            start_char=token.idx,
            end_char=token.idx + len(token.text)
        ) for token in doc if not token.is_space
    ] # exclude whitespace tokens

    return tokens
