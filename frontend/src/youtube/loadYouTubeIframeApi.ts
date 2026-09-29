// Loads YouTube's IFrame Player API script exactly once, however many
// components ask for it, and resolves once `window.YT` is actually usable.
let apiReady: Promise<typeof YT> | null = null

export function loadYouTubeIframeApi(): Promise<typeof YT> {
  // Vite HMR can remount components without a full page reload, so the
  // script may already be sitting there from a previous mount.
  if (window.YT?.Player) return Promise.resolve(window.YT)
  if (apiReady) return apiReady

  apiReady = new Promise((resolve) => {
    // YouTube announces readiness by calling this *global* function itself —
    // not the <script> tag's own onload event — so it must exist by the
    // time the script finishes loading, not just after we append it.
    window.onYouTubeIframeAPIReady = () => resolve(window.YT)

    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(script)
  })

  return apiReady
}
