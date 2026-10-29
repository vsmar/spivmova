// Inspired by https://translit.cc/ua schema
// https://en.wikipedia.org/wiki/Transliteration_of_Ukrainian#Standardization

export const SINGLE: Record<string, string> = {
    a: 'а',
    b: 'б',
    v: 'в',
    w: 'в', 
    h: 'г',
    g: 'ґ',
    d: 'д',
    e: 'е',
    z: 'з',
    y: 'и',
    i: 'і',
    j: "й",
    k: "к",
    l: "л",
    m: "м",
    n: "н",
    o: "о",
    p: "п",
    r: "р",
    s: "с",
    t: "т",
    u: "у",
    f: "ф",
    x: "х",
    c: "ц",
    "\"": 'ь', 
    "'": 'ʼ'
}

// key → { previous Cyrillic letter → combined result }
// undoText in translit.ts relies on the fact that combine works off of single entry
export const COMBINE: Record<string, Record<string, string>> = {
  h: { з: 'ж', с: 'ш', ц: 'ч', ш: 'щ', к: 'х', ґ: 'г' },   // shh = ш+h, kh alias
  a: { и: 'я', й: 'я' },
  u: { и: 'ю', й: 'ю' },
  e: { и: 'є', й: 'є' },
  i: { и: 'ї', й: 'ї' },
}
export const ESCAPE = '\\' // Backslash: common escape character