import { useEffect, useRef, useState, type SubmitEvent } from 'react'
import './App.css'

import { getTrackVideo, searchTrack, setTrackVideo, TrackNotFoundError, ApiError } from './api/clients'
import type { TrackOut, LyricLineOut, TokenOut, VideoOut } from './api/types'
import { SpivmovaLogo } from "./components/SpivmovaLogo";
import { loadYouTubeIframeApi } from './youtube/loadYouTubeIframeApi'


type FetchState<T> =
| { status: 'idle'; data: null; error: null }
| { status: 'loading'; data: null; error: null }
| { status: 'success'; data: T; error: null }
| { status: 'error'; data: null; error: Error };

type SearchBarProps = {
  onSearch: (track: string, artist: string, album?: string, duration?: number) => void
  loading: boolean
}

type TokenProps = {
  token: TokenOut
  isRelated: boolean
  // Reports this token's vocab_id on hover/focus (null on leave/blur) so
  // Lyrics can highlight every other token that shares it.
  onHover: (vocabId: number | null) => void
}

export const SearchBar = ({ onSearch, loading }: SearchBarProps) => {
  const [trackName, setTrackName] = useState('')
  const [artistName, setArtistName] = useState('')
  const [albumName, setAlbumName] = useState('')
  const [duration, setDuration] = useState<number | null>(null)

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault()
    onSearch(trackName, artistName, albumName || undefined, duration ?? undefined)
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Track Name"
        value={trackName}
        required={true}
        onChange={(e) => setTrackName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Artist Name"
        value={artistName}
        required={true}
        onChange={(e) => setArtistName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Album Name"
        value={albumName}
        onChange={(e) => setAlbumName(e.target.value)}
      />
      <input
        type="number"
        placeholder="Duration (seconds)"
        value={duration ?? ''}
        onChange={(e) => setDuration(e.target.value ? Number(e.target.value) : null)}
      />
      <button type="submit" disabled={loading}>
        Search
      </button>
    </form>
  )
}

export const Token = ({ token, isRelated, onHover }: TokenProps) => {
  // Punctuation isn't a vocab item — render as plain text, not a button.
  if (token.pos === 'PUNCT') {
    return <span className="token punct">{token.text}</span>
  }
  return (
    <button
      type="button"
      className={`token word${isRelated ? ' related' : ''}`}
      onMouseEnter={() => onHover(token.vocab_id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(token.vocab_id)}
      onBlur={() => onHover(null)}
    >
      {token.text}
      {/* Shown via CSS on :hover/:focus-visible — see .token-tooltip in App.css */}
      <span className="token-tooltip">
        <strong>{token.lemma}</strong> <em>{token.pos}</em>
        <br />
        {token.sense ?? 'No translation available'}
      </span>
    </button>
  )
}

export const VideoPane = ({ trackId, onTimeUpdate, onReady }: {
  trackId: number,
  onTimeUpdate: (time: number) => void,
  onReady: (isReady: YT.PlayerEvent) => void,
}) => {
  const [video, setVideo] = useState<FetchState<VideoOut>>({ status: 'idle', data: null, error: null })
  const [overrideId, setOverrideId] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const videoId = video.status === 'success' && video.data.youtube_video_id ? video.data.youtube_video_id : null
  const intervalRef = useRef<number | null>(null)
  const playerRef = useRef<YT.Player | null>(null)

  // Re-fetch whenever the track changes. `cancelled` guards against a race:
  // if trackId changes again before this request resolves, its (stale)
  // result must not overwrite the state for the newer track.
  useEffect(() => {
    let cancelled = false
    setVideo({ status: 'loading', data: null, error: null })
    getTrackVideo(trackId)
      .then((data) => {
        if (!cancelled) setVideo({ status: 'success', data, error: null })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setVideo({ status: 'error', data: null, error: err instanceof Error ? err : new Error(String(err)) })
        }
      })
    return () => {
      cancelled = true
    }
  }, [trackId])

  const handleOverride = async (e: SubmitEvent) => {
    e.preventDefault()
    const id = overrideId.trim()
    if (!id) return
    try {
      const data = await setTrackVideo(trackId, { youtube_video_id: id })
      setVideo({ status: 'success', data, error: null })
      setOverrideId('')
    } catch (err) {
      setVideo({ status: 'error', data: null, error: err instanceof Error ? err : new Error(String(err)) })
    }
  }

  function onStateChange(event: YT.OnStateChangeEvent) {
    if (event.data === YT.PlayerState.PLAYING) {
      intervalRef.current = window.setInterval(() => {
        onTimeUpdate(event.target.getCurrentTime() * 1000)
      }, 250)
    } else if (intervalRef.current !== null) {
      clearInterval(intervalRef.current) 
      intervalRef.current = null
    }
  }

  useEffect(() => {
    if (videoId === null) return
      let cancelled = false

    loadYouTubeIframeApi().then((YT) => {
      if (cancelled) return
      playerRef.current?.destroy()
      const player = new YT.Player(containerRef.current!, {
        videoId: videoId ?? undefined,
        events: { onReady, onStateChange },
      })
      playerRef.current = player
    })

    return () => {
      cancelled = true
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      playerRef.current?.destroy()
      playerRef.current = null
    }
  }, [videoId])

  if (video.status === 'success' && video.data.youtube_video_id) {
    return (
      <div ref={containerRef} className="video-pane" />
    )
  } else {
    return (
      <div className="video-pane video-pane--empty">
        <p>
          {video.status === 'loading' && 'Looking for a video…'}
          {video.status === 'error' && 'Could not load video.'}
          {video.status === 'success' && 'No video found for this track.'}
        </p>
        <form onSubmit={handleOverride}>
          <input
            type="text"
            placeholder="YouTube video ID"
            value={overrideId}
            onChange={(e) => setOverrideId(e.target.value)}
          />
          <button type="submit">Set</button>
        </form>
      </div>
    )
  }
}


// 'hidden' and 'always' are permanent states; 'hover' reveals a line's
// translation only while that line is hovered.
type TranslationMode = 'hidden' | 'always' | 'hover'
const TRANSLATION_MODES: { value: TranslationMode; label: string }[] = [
  { value: 'hidden', label: 'Hide' },
  { value: 'always', label: 'Always' },
  { value: 'hover', label: 'On hover' },
]

export const Lyrics = ({ track, lines }: { track: TrackOut; lines: LyricLineOut[] }) => {
  const [hoveredVocabId, setHoveredVocabId] = useState<number | null>(null)
  const [translationMode, setTranslationMode] = useState<TranslationMode>('always')
  const sorted = [...lines].sort((a, b) => a.position - b.position)
  const [currentTime, setCurrentTime] = useState(0)
  const [isReady, setIsReady] = useState<YT.PlayerEvent | null>(null)
  const [isFollowing, setFollowing] = useState(true) 
  const activeLineRef = useRef<HTMLDivElement | null>(null)

  const activePosition = sorted.findLast(
    (line) => line.time !== null && line.time <= currentTime
  )?.position ?? null

  useEffect(() => {
    if (isFollowing) activeLineRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [activePosition, isFollowing])


  return (
    <div className="player">
      <VideoPane trackId={track.id} onTimeUpdate={setCurrentTime} onReady={setIsReady} />
      <div className="lyrics-pane">
        <div className="lyrics-header">
          <h2>{track.track_name} - {track.artist_name}</h2>
        </div>
        <div className="translation-mode" role="radiogroup" aria-label="Line translations">
          {TRANSLATION_MODES.map((mode) => (
            <label key={mode.value}>
              <input
                type="radio"
                name="translation-mode"
                checked={translationMode === mode.value}
                onChange={() => setTranslationMode(mode.value)}
              />
              {mode.label}
            </label>
          ))}
        </div>
        <div className="lyrics-scroll">
          {sorted.map((line) => (
            <div ref={line.position === activePosition ? activeLineRef : undefined} 
            className={`lyric-line${line.position === activePosition ? ' active' : ''}`} 
            key={line.position}>
              <p>{renderLine(line, currentTime, hoveredVocabId, setHoveredVocabId)}</p>
              {/* Always rendered (when a translation exists) so the line's height
                  never changes — visibility/opacity hide it, not conditional rendering. */}
              {line.translation && (
                <p className={`line-translation line-translation--${translationMode}`}>
                  {line.translation}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export const renderLine = (
  line: LyricLineOut,
  currentTime: number,
  hoveredVocabId: number | null,
  onHover: (vocabId: number | null) => void,
) => {
  // Slice by start_char/end_char (rather than joining token.text with spaces)
  // so the rendered line matches the original exactly, gaps included.
  const sorted = [...line.tokens].sort((a, b) => a.start_char - b.start_char)
  const pieces: React.ReactNode[] = []
  let cursor = 0

  for (const token of sorted) {
    if (token.start_char > cursor) {
      pieces.push(line.text.slice(cursor, token.start_char))
    }
    const isRelated = token.vocab_id !== null && token.vocab_id === hoveredVocabId
    pieces.push(
      <Token key={`${line.position}-${token.position}`} token={token} isRelated={isRelated} onHover={onHover} />,
    )
    cursor = token.end_char
  }
  if (cursor < line.text.length) pieces.push(line.text.slice(cursor))

  return pieces
}


function describeError(err: Error): string {
  if (err instanceof TrackNotFoundError) return 'No lyrics found for that song and artist.'
  if (err instanceof ApiError && err.status === 502) return err.message
  if (err instanceof TypeError) return 'No response from the server (it may be down or have crashed).'
  return 'Something went wrong.'
}

function App() {
  const [search, setSearch] = useState<FetchState<TrackOut>>({
    status: 'idle', 
    data: null, 
    error: null 
  });

  const handleSearch = async (track: string, artist: string, album?: string, duration?: number) => {
    setSearch({ status: 'loading', data: null, error: null })
    try {
      const data = await searchTrack(track, artist, album, duration)
      setSearch({ status: 'success', data, error: null })
    } catch (err) {
      setSearch({
        status: 'error',
        data: null,
        error: err instanceof Error ? err : new Error(String(err)),
      })
    }
  }

  return (
    <>
      <section id="center">
        <SpivmovaLogo />
        <p> Learning Ukrainian through song. </p>

        <SearchBar onSearch={handleSearch} loading={search.status === 'loading'} />
        {search.status === 'loading' && (
          <>
            <h3>Searching...</h3>
            <p>New songs can take a while</p>
          </>
        )}
        {search.status === 'error' && (
          <p>{describeError(search.error)}</p>
        )}
        {search.status === 'success' && <Lyrics track={search.data} lines={search.data.lines} />}
      </section>

      <a id="social" href="https://github.com/vsmar/spivmova" target="_blank" aria-label="GitHub repository">
        <svg className="button-icon" role="presentation" aria-hidden="true">
          <use href="/icons.svg#github-icon"></use>
        </svg>
      </a>
    </>
  )
}

export default App
