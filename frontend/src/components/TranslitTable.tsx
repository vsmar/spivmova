import { useLayoutEffect, useRef, useState } from 'react';
import { SINGLE, COMBINE, ESCAPE } from '../translit/scheme'
import './TranslitTable.css'


export type keyRow = { cyr: string; keys: string[] }

const alphabet: string = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюяʼ"

export function buildKeyTable(): keyRow[] {
    const rows: keyRow[] = []
    const translitDict: Record<string, string[]> = {}

    Object.entries(SINGLE).forEach(([key, value]) => {
        (translitDict[value] ??= []).push(key);
    });

    let changed = true
    let rounds = 0
    while (changed && rounds < 4) {
        changed = false
        for (const [key, rules] of Object.entries(COMBINE)) {
            for (const [prev, combined] of Object.entries(rules)) {
                for (const seq of translitDict[prev] ?? []) {
                    const list = (translitDict[combined] ??= [])
                    if (!list.includes(seq + key)) {
                        list.push(seq + key)
                        changed = true
                    }
                }
            }
        }
        rounds++
    }

    if (changed) {
        console.warn("Translit scheme may have a cyclic graph")
    }
    
    for (const c of alphabet) {
        if (translitDict[c]) rows.push({ cyr: c, keys: translitDict[c] ?? [] })
    }
    // rows.push({ cyr: "escape", keys: [ESCAPE] })
    return rows
}

const ROWS = buildKeyTable()

export function TranslitTable({ onInsert }: { onInsert: (text: string) => void }) {
    const tableRef = useRef<HTMLDivElement>(null)
    const [below, setBelow] = useState(false)

    useLayoutEffect(() => {
        const top = tableRef.current?.getBoundingClientRect().top ?? 0
        if (top < 8) setBelow(true)          // would be cut off at the top of the window
    }, [])

    return (
        <div ref={tableRef} className={`translit-table${below ? ' translit-table--below' : ''}`} role="group" aria-label="Cyrillic letters">
            <div className="translit-keys">
                {ROWS.map((row) => (
                <button
                    key={row.cyr}
                    type="button"
                    className="translit-key"
                    onMouseDown={(e) => e.preventDefault()}   // keep focus in the input
                    onClick={(e) => onInsert(e.shiftKey ? row.cyr.toUpperCase() : row.cyr)}
                >
                    <span className="translit-cyr">{row.cyr}</span>
                    <span className="translit-lat">
                        {row.keys[0]}
                        {row.keys.length > 1 && <span className="translit-alias"> {row.keys.slice(1).join(' ')}</span>}
                    </span>
                </button>
                ))}
            </div>

            <details className="translit-hints">
                <summary onMouseDown={(e) => e.preventDefault()}>Hints</summary>
                <div className="translit-hint-group">
                    <p className="translit-hint-label">Typing</p>
                    <dl className="translit-hint">
                        <dt><kbd>{ESCAPE}</kbd></dt> <dd>keep letters separate: z{ESCAPE}h → зг</dd>
                        <dt><kbd>Backspace</kbd></dt> <dd>undo a combination: ж → зг</dd>
                    </dl>
                </div>
                <div className="translit-hint-group">
                    <p className="translit-hint-label">Clicking</p>
                    <dl className="translit-hint">
                        <dt><kbd>Shift</kbd> + click</dt> <dd>capital letter</dd>
                    </dl>
                </div>
            </details>
        </div>
    )
}
