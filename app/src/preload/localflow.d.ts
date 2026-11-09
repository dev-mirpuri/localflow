declare global {
  /** A message from the Engine, as in the protocol in docs/PROJECT_BRIEF.md section 4. */
  type EngineMessage = { type: string; [key: string]: unknown }

  interface LocalFlow {
    /** Calls back with each Engine message except replies; returns a function that stops it. */
    onEvent(callback: (message: EngineMessage) => void): () => void
    request(method: string, params: Record<string, unknown>): Promise<unknown>
    command(name: 'finish' | 'cancel'): void
    copy(text: string): void
    /** Shows the Oval window around a pill this wide, or hides it when null. */
    showOval(pill: { width: number; clickable: boolean } | null): void
  }

  interface Window {
    localflow?: LocalFlow // Missing in a normal browser, where the Fake bridge stands in.
  }
}

export {}
