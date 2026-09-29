// @types/youtube declares the `YT` namespace (Player, PlayerState, etc.) as
// an ambient global, but doesn't know it ends up on `window`, or about
// YouTube's own "API is ready" callback. These two lines are what's missing.
export {}

declare global {
  interface Window {
    YT: typeof YT
    onYouTubeIframeAPIReady?: () => void
  }
}
