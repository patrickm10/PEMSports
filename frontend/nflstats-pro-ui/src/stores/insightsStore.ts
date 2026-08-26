import { create } from 'zustand';
import type { InsightContext, InsightPosition } from '../api/insightsTypes';

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

export const useInsightsStore = create<InsightsStore>((set) => ({
  position: 'rb',
  context: 'surface',
  contextValue: 'Grass',
  selectedPlayerId: null,
  selectedPlayerPosition: null,
  setPosition: (position) =>
    set({ position, selectedPlayerId: null, selectedPlayerPosition: null }),
  setContext: (context) =>
    set({ context, selectedPlayerId: null, selectedPlayerPosition: null }),
  setContextValue: (contextValue) =>
    set({ contextValue, selectedPlayerId: null, selectedPlayerPosition: null }),
  selectPlayer: (playerId, position) =>
    set({ selectedPlayerId: playerId, selectedPlayerPosition: position }),
  clearPlayer: () => set({ selectedPlayerId: null, selectedPlayerPosition: null }),
}));
