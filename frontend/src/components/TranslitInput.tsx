import { useImperativeHandle, useLayoutEffect, useRef, type ComponentProps, type KeyboardEvent, type Ref } from 'react';
import { step } from '../translit/translit'
import './TranslitInput.css'

export type TranslitInputHandle = { insert: (text: string) => void }

type TranslitInputProps = Omit<ComponentProps<'input'>, 'value' | 'onChange' | 'ref'> & {
    value: string
    onChange: (value: string) => void
    translit: boolean
    ref?: Ref<TranslitInputHandle>
}

type Combo = { pos: number; undoText: string }

export function TranslitInput({ value, onChange, translit, ref, ...rest }: TranslitInputProps) {
    const inputRef = useRef<HTMLInputElement>(null)
    const pendingCaret = useRef<number | null>(null)
    const lastCombo = useRef<Combo | null>(null)

    useLayoutEffect(() => {
        if (pendingCaret.current !== null && inputRef.current) {
            inputRef.current.setSelectionRange(pendingCaret.current, pendingCaret.current)
            pendingCaret.current = null
        }
    }, [value])

    const replaceRange = (from: number, to: number, text: string) => {
        pendingCaret.current = from + text.length
        onChange(value.slice(0, from) + text + value.slice(to))
    }

    useImperativeHandle(ref, () => ({
        insert(text: string) {
            const el = inputRef.current
            if (!el) return
            lastCombo.current = null
            replaceRange(el.selectionStart ?? value.length, el.selectionEnd ?? value.length, text)
        },
    }))

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        const start = e.currentTarget.selectionStart ?? 0
        const end = e.currentTarget.selectionEnd ?? 0

        // Handle undo of a combined translit sequence
        if (e.key ==='Backspace') {
            if (lastCombo.current !== null) {
                if (lastCombo.current.pos === start && start === end) {
                    e.preventDefault()
                    replaceRange(start - 1, start, lastCombo.current.undoText)
                }
                lastCombo.current = null
            }
            return
        }

        // Handle inputs that avoid translit (NOTE: french keyboards have / behind AltGr, requires ctrl)
        const hasModifier = e.ctrlKey || e.metaKey || e.altKey
        if (!translit || e.key.length !== 1 || (hasModifier && !e.getModifierState('AltGraph'))) {
        // if (!translit || e.key.length !== 1 || (e.ctrlKey && !e.altKey) || e.metaKey) {
            lastCombo.current = null
            return
        }

        const prev = (start === end) ? (value[start - 1] ?? '') : ''
        const result = step(prev, e.key)
        if (result === null) {
            lastCombo.current = null
            return
        }

        e.preventDefault()
        const from = result.replacePrev ? start - 1 : start
        const caret = from + result.insert.length
        replaceRange(from, end, result.insert)
        lastCombo.current = result.undoText ? { pos: caret, undoText: result.undoText } : null 
    }

    return (
        <input
            {...rest}
            ref={inputRef}
            value={value}
            onChange={e => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
        />
    )
}
