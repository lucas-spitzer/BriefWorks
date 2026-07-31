import { useCallback, useSyncExternalStore } from 'react'
import type { OutputItem } from './learnerOutputs'

// Per-workspace "focus" flags for library items, persisted in localStorage
// (same pattern as the reader bookmark). Focused items float to the top of
// their tab in the Library; at most one ebook can be focused, and that
// ebook's source becomes the default book in the Reader.
export interface LibraryFocusState {
  /** Item keys (`${kind}-${id}`) of focused non-ebook items. */
  keys: string[]
  /** Item key of the focused ebook artifact, if any. */
  ebookKey: string | null
  /** Source id of the focused ebook — the Reader's default book. */
  ebookSourceId: string | null
}

const EMPTY_FOCUS: LibraryFocusState = { keys: [], ebookKey: null, ebookSourceId: null }
const FOCUS_EVENT = 'briefworks:library-focus'

export function focusItemKey(item: Pick<OutputItem, 'kind' | 'id'>): string {
  return `${item.kind}-${item.id}`
}

function storageKey(workspaceId: string): string {
  return `briefworks:library-focus:${workspaceId}`
}

// Cache parsed snapshots so useSyncExternalStore gets referentially stable
// values between changes.
const focusCache = new Map<string, LibraryFocusState>()

function readState(workspaceId: string | null): LibraryFocusState {
  if (!workspaceId) return EMPTY_FOCUS
  const cached = focusCache.get(workspaceId)
  if (cached) return cached
  let state = EMPTY_FOCUS
  try {
    const raw = localStorage.getItem(storageKey(workspaceId))
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<LibraryFocusState>
      state = {
        keys: Array.isArray(parsed.keys)
          ? parsed.keys.filter((key) => typeof key === 'string')
          : [],
        ebookKey: typeof parsed.ebookKey === 'string' ? parsed.ebookKey : null,
        ebookSourceId:
          typeof parsed.ebookSourceId === 'string' ? parsed.ebookSourceId : null,
      }
    }
  } catch {
    state = EMPTY_FOCUS
  }
  focusCache.set(workspaceId, state)
  return state
}

function writeState(workspaceId: string, state: LibraryFocusState) {
  focusCache.set(workspaceId, state)
  try {
    localStorage.setItem(storageKey(workspaceId), JSON.stringify(state))
  } catch {
    // Persistence is best-effort; the in-memory state still applies.
  }
  window.dispatchEvent(new Event(FOCUS_EVENT))
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(FOCUS_EVENT, onChange)
  return () => window.removeEventListener(FOCUS_EVENT, onChange)
}

export function isFocused(state: LibraryFocusState, item: Pick<OutputItem, 'kind' | 'id'>): boolean {
  const key = focusItemKey(item)
  return state.ebookKey === key || state.keys.includes(key)
}

export function useLibraryFocus(workspaceId: string | null): {
  focus: LibraryFocusState
  toggleFocus: (item: OutputItem) => void
} {
  const focus = useSyncExternalStore(subscribe, () => readState(workspaceId))

  const toggleFocus = useCallback(
    (item: OutputItem) => {
      if (!workspaceId) return
      const state = readState(workspaceId)
      const key = focusItemKey(item)
      if (isFocused(state, item)) {
        writeState(workspaceId, {
          keys: state.keys.filter((focusedKey) => focusedKey !== key),
          ebookKey: state.ebookKey === key ? null : state.ebookKey,
          ebookSourceId: state.ebookKey === key ? null : state.ebookSourceId,
        })
        return
      }
      if (item.isEbook) {
        // Only one ebook can be focused at a time; the new one replaces it.
        writeState(workspaceId, {
          keys: state.keys,
          ebookKey: key,
          ebookSourceId: item.sourceId,
        })
        return
      }
      writeState(workspaceId, { ...state, keys: [...state.keys, key] })
    },
    [workspaceId],
  )

  return { focus, toggleFocus }
}
