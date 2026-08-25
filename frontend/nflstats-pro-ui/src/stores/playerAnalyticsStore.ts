import { create } from 'zustand';
import type { AnalyticsPanel, PlayerRef } from './types';
import { ALL_ANALYTICS_PANELS } from './types';

interface PlayerAnalyticsState {
  selectedPlayer: PlayerRef | null;
  comparisonPlayer: PlayerRef | null;
  activePanels: ReadonlySet<AnalyticsPanel>;
}

interface PlayerAnalyticsActions {
  selectPlayer: (p: PlayerRef) => void;
  setComparison: (p: PlayerRef | null) => void;
  togglePanel: (k: AnalyticsPanel) => void;
  clear: () => void;
}

const DEFAULT_STATE: PlayerAnalyticsState = {
  selectedPlayer: null,
  comparisonPlayer: null,
  activePanels: new Set<AnalyticsPanel>(ALL_ANALYTICS_PANELS),
};

/**
 * UI-only store for the player-analytics surface.
 *
 * Boundary rule: this store mutates PURE UI state. It does not change
 * navigation (workspaceView / activeTab). The App layer subscribes to
 * `selectedPlayer` and updates navigation imperatively in a useEffect.
 * Server data (splits, weekly logs, metadata) lives in React Query.
 */
export const usePlayerAnalyticsStore = create<
  PlayerAnalyticsState & PlayerAnalyticsActions
>()((set) => ({
  ...DEFAULT_STATE,
  selectPlayer: (p) =>
    set((s) => ({
      selectedPlayer: p,
      comparisonPlayer:
        s.selectedPlayer?.player_id === p.player_id ? s.comparisonPlayer : null,
    })),
  setComparison: (p) => set({ comparisonPlayer: p }),
  togglePanel: (k) =>
    set((s) => {
      const next = new Set(s.activePanels);
      if (next.has(k)) next.delete(k);
      else next.add(k);
      return { activePanels: next };
    }),
  clear: () =>
    set({
      selectedPlayer: null,
      comparisonPlayer: null,
      activePanels: new Set<AnalyticsPanel>(ALL_ANALYTICS_PANELS),
    }),
}));
