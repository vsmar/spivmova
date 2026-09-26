export type LyricLineOut = {
    position: number
    time: number | null
    text: string
    translation: string | null
    tokens: TokenOut[]
}

export type TokenOut = {
    position: number
    text: string
    start_char: number
    end_char: number
    vocab_id: number | null
    lemma: string | null
    pos: string | null
    sense: string | null
}

export type TrackOut = {
    id: number
    track_name: string
    artist_name: string
    album_name: string | null
    duration: number | null
    lines: LyricLineOut[]
}

export type VideoOut = {
    youtube_video_id: string | null
}

export type VideoOverrideIn = {
    youtube_video_id: string
}

export type VocabOut = {
    lemma: string
    pos: string
    senses: SenseOut[]
}

export type SenseOut = {
    translation: string
    provider: string
    example_line_id: number | null
}

