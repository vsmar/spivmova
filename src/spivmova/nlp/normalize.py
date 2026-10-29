"""Transliteration & Normalization (collapsing symbols, accent removal, folding disambiguation)"""



def transliterate(text: str) -> str:
    """
    Transliterate Ukrainian text to Latin script using the official Ukrainian government rules.
    https://en.wikipedia.org/wiki/Romanization_of_Ukrainian

    Notes: national 1996 system saw double consonants simplified to single
    """
    # import transliterate

    OFFICIAL_UK_L_MAPPINGS = {
        "зг": "zgh", # used to avoid ambiguit with ж/zh
        " є": " ye", # used when starting a word
        " ї": " yi", # used when starting a word
        " й": " y", # used when starting a word
        " ю": " yu", # used when starting a word
        " я": " ya", # used when starting a word

        "а": "a",
        "б": "b",
        "в": "v",
        "г": "h",
        "ґ": "g",
        "д": "d",
        "е": "e",
        "є": "ie",
        "ж": "zh",
        "з": "z",
        "и": "y",
        "i": "i",
        "ї": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ь": "", # sometimes "'"
        "ю": "iu",
        "я": "ia",
    }

    OFFICIAL_EN_UKR_MAPPINGS = {
        # NOTE: can maybe remove the leading space for reverse mapping?
        "zgh": "зг", # used to avoid ambiguit with ж/zh
        " ye": " є", # used when starting a word
        " yi": " ї", # used when starting a word
        " y": " й", # used when starting a word
        " yu": " ю", # used when starting a word
        " ya": " я", # used when starting a word

        "a": "а",
        "b": "б",
        "v": "в",
        "h": "г",
        "g": "ґ",
        "d": "д",
        "e": "е",
        "ie": "є",
        "zh": "ж",
        "z": "з",
        "y": "и",
        "i": "i",
        "i": "ї",
        "i": "й",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "f": "ф",
        "kh": "х",
        "ts": "ц",
        "ch": "ч",
        "sh": "ш",
        "shch": "щ",
        "'": "ь",
        "iu": "ю",
        "ia": "я",
    }

    