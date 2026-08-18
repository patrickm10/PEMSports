import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { PlayerRef } from './types';
import { dropLegacyRecents } from './searchRecents';

const RECENT_LIMIT = 5;

interface SearchState {
  isOpen: boolean;
  query: string;
  recentPlayers: PlayerRef[];
}

interface SearchActions {
  open: () => void;
  close: () => void;
  toggle: () => void;
  setQuery: (q: string) => void;
  clearQuery: () => void;
  pushRecent: (p: PlayerRef) => void;
  clearRecent: () => void;
}

const DEFAULT_STATE: SearchState = {
  isOpen: false,
  query: '',
  recentPlayers: [],
};

/**
 * UI-only store for the global search modal.
 * Owns: open/closed, query, recent selections.
 * Does NOT own: navigation, position tab, workspace view.
 */
export const useSearchStore = create<SearchState & SearchActions>()(
  persist(
    (set) => ({
      ...DEFAULT_STATE,
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      toggle: () => set((s) => ({ isOpen: !s.isOpen })),
      setQuery: (q) => set({ query: q }),
      clearQuery: () => set({ query: '' }),
      pushRecent: (p) =>
        set((s) => {
          const filtered = s.recentPlayers.filter(
            (r) => r.player_id !== p.player_id,
          );
          return {
            recentPlayers: [p, ...filtered].slice(0, RECENT_LIMIT),
          };
        }),
      clearRecent: () => set({ recentPlayers: [] }),
    }),
    {
      name: 'nflstats:search',
      version: 2,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ recentPlayers: s.recentPlayers }),
      migrate: (persisted, version) => {
        const state = persisted as SearchState;
        if (version < 2) {
          return {
            ...DEFAULT_STATE,
            ...state,
            recentPlayers: dropLegacyRecents(state.recentPlayers ?? []),
          };
        }
        return state;
      },
    },
  ),
);
