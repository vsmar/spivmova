import { SINGLE, COMBINE, ESCAPE } from './scheme'

const isUpper = (ch: string) => ch !== ch.toLowerCase()
const matchCase = (s: string, upper: boolean) => (upper ? s.toUpperCase() : s)

export type StepResult = { replacePrev: boolean; insert: string; undoText: string | null }

// Given the char before the caret and the typed key, decide what happens
export function step(prev: string, key: string): StepResult | null {
    if (key === ESCAPE) return { replacePrev: false, insert: ESCAPE, undoText: null }

    const keyLower = key.toLowerCase()
    const single = SINGLE[keyLower]

    if (prev === ESCAPE) {
        return { replacePrev: true, insert: single ? (matchCase(single, isUpper(key))) : key, undoText: null }
    }

    if (prev && COMBINE[keyLower]?.[prev.toLowerCase()]) {
        const prev_lower = prev.toLowerCase()
        return { 
            replacePrev: true, 
            insert: matchCase(COMBINE[keyLower][prev_lower], isUpper(prev)),
            undoText: prev + (matchCase(single, isUpper(key)))
        }
    }
    return single ? { replacePrev: false, insert: matchCase(single, isUpper(key)), undoText: null } : null
}

