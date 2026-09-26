import { useState } from 'react'
import heroImg from './assets/hero.png'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import './App.css'

import { searchTrack, TrackNotFoundError } from './api/clients'
import type { TrackOut } from './api/types'


type FetchState<T> =
| { status: 'idle'; data: null; error: null }
| { status: 'loading'; data: null; error: null }
| { status: 'success'; data: T; error: null }
| { status: 'error'; data: null; error: Error };

type SearchBarProps = {
  onSearch: (track: string, artist: string, album?: string, duration?: number) => void
  loading: boolean
}

export const SearchBar = ({ onSearch, loading }: SearchBarProps) => {
  const [trackName, setTrackName] = useState('')
  const [artistName, setArtistName] = useState('')
  const [albumName, setAlbumName] = useState('')
  const [duration, setDuration] = useState<number | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(trackName, artistName, albumName || undefined, duration ?? undefined)
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Track Name"
        value={trackName}
        onChange={(e) => setTrackName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Artist Name"
        value={artistName}
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


  // state.error instanceof TrackNotFoundError



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
        <div className="hero">
          <img src={heroImg} className="base" width="170" height="179" alt="" />
          <img src={reactLogo} className="framework" alt="React logo" />
          <img src={viteLogo} className="vite" alt="Vite logo" />
        </div>
        <div>
          <h1>spivmova</h1>
          <p>
            Learning Ukrainian through song.
          </p>
        </div>
        <SearchBar onSearch={handleSearch} loading={search.status === 'loading'} />
      </section>

      <div className="ticks"></div>

      <section id="next-steps">
        <div id="docs">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#documentation-icon"></use>
          </svg>
          <h2>Documentation</h2>
          <p>Your questions, answered</p>
          <ul>
            <li>
              <a href="https://vite.dev/" target="_blank">
                <img className="logo" src={viteLogo} alt="" />
                Explore Vite
              </a>
            </li>
            <li>
              <a href="https://react.dev/" target="_blank">
                <img className="button-icon" src={reactLogo} alt="" />
                Learn more
              </a>
            </li>
          </ul>
        </div>
        <div id="social">
          <svg className="icon" role="presentation" aria-hidden="true">
            <use href="/icons.svg#social-icon"></use>
          </svg>
          <h2>Learn More</h2>
          <p>Codebase</p>
          <ul>
            <li>
              <a href="https://github.com/vsmar/spivmova" target="_blank">
                <svg
                  className="button-icon"
                  role="presentation"
                  aria-hidden="true"
                >
                  <use href="/icons.svg#github-icon"></use>
                </svg>
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </section>

      <div className="ticks"></div>
      <section id="spacer"></section>
    </>
  )
}

export default App
