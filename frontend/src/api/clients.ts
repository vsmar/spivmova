import type { TrackOut, VideoOut, VideoOverrideIn } from './types'

const API_BASE = 'http://127.0.0.1:8000'

export class TrackNotFoundError extends Error {
  constructor() {
    super('Track not found')
    this.name = 'TrackNotFoundError'
  }
}

export async function getTrackVideo(trackId: number): Promise<VideoOut> {
    const res = await fetch(`${API_BASE}/tracks/${trackId}/video`)
    if (!res.ok) {
        throw new Error(`Request failed for track ${trackId}: ${res.statusText}`)
    }
    return res.json()
}

export async function setTrackVideo(trackId: number, videoOverride: VideoOverrideIn): Promise<VideoOut> {
    const res = await fetch(`${API_BASE}/tracks/${trackId}/video`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(videoOverride),
    })
    if (!res.ok) {
        throw new Error(`Request failed for track ${trackId}: ${res.statusText}`)
    }
    return res.json()
}

export async function searchTrack(trackName: string, artistName: string, albumName?: string, duration?: number): Promise<TrackOut> {
    const params = new URLSearchParams({
        track: trackName,
        artist: artistName,
    })
    if (albumName !== undefined) params.set('album', albumName)
    if (duration !== undefined) params.set('duration', String(duration))

    const res = await fetch(`${API_BASE}/tracks/search?${params.toString()}`)
    if (res.status === 404) throw new TrackNotFoundError()
    if (!res.ok) {
        throw new Error(`Request failed for search: ${res.statusText}`)
    }
    return res.json()
}

