import { create } from 'zustand';
import type { InsightContext, InsightPosition } from '../api/insightsTypes';

/**
 * Insights workspace selection.
 *
 * Player selection is cleared when position, context, or context value changes
 * because the selected player may not appear on the next leaderboard. Season and
 * week live in App (ControlBar) and do not clear selection — player detail
 * refetches for the new filters instead.
 *
 * Context value is reset on context change (Grass for surface; empty until
 * /insights/contexts returns values for opponent, stadium, and home_away).
 */
interface InsightsStore {
  position: InsightPosition;
  context: InsightContext;
  contextValue: string;
  selectedPlayerId: string | null;
  selectedPlayerPosition: Exclude<InsightPosition, 'all'> | null;
  setPosition: (position: InsightPosition) => void;
  setContext: (context: InsightContext) => void;
  setContextValue: (value: string) => void;
  selectPlayer: (playerId: string, position: Exclude<InsightPosition, 'all'>) => void;
  clearPlayer: () => void;
}

function defaultValueForContext(context: InsightContext): string {
  return context === 'surface' ? 'Grass' : '';
}

export const useInsightsStore = create<InsightsStore>((set) => ({
  position: 'rb',
  context: 'surface',
  contextValue: 'Grass',
  selectedPlayerId: null,
  selectedPlayerPosition: null,
  setPosition: (position) =>
    set({ position, selectedPlayerId: null, selectedPlayerPosition: null }),
  setContext: (context) =>
    set({
      context,
      contextValue: defaultValueForContext(context),
      selectedPlayerId: null,
      selectedPlayerPosition: null,
    }),
  setContextValue: (contextValue) =>
    set({ contextValue, selectedPlayerId: null, selectedPlayerPosition: null }),
  selectPlayer: (playerId, position) =>
    set({ selectedPlayerId: playerId, selectedPlayerPosition: position }),
  clearPlayer: () => set({ selectedPlayerId: null, selectedPlayerPosition: null }),
}));
