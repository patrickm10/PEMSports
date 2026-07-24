import React, { useEffect, useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { usePlayerAnalyticsStore } from '../../../stores/playerAnalyticsStore';
import { useSearchStore } from '../../../stores/searchStore';
import { usePlayerAnalytics } from '../../../hooks/usePlayerAnalytics';
import { AnalyticsHeader } from './AnalyticsHeader';
import { VsOpponentPanel } from './panels/VsOpponentPanel';
import { StadiumPanel } from './panels/StadiumPanel';
import { SurfacePanel } from './panels/SurfacePanel';
import { WeeklyTrendPanel } from './panels/WeeklyTrendPanel';
import { MetadataOverlayPanel } from './panels/MetadataOverlayPanel';

interface PlayerAnalyticsViewProps {
  /**
   * Callback fired when the user requests to leave the analytics view.
   * Owned by the App so navigation stays out of the store.
   */
  onBack: () => void;
}

/**
 * Composes the analytics dashboard for the currently selected player.
 *
 * - Reads selection state from `usePlayerAnalyticsStore`.
 * - Calls the single orchestration hook `usePlayerAnalytics`.
 * - Distributes pre-normalized chart-contract slices to presentational panels.
 *
 * No fetching or normalization happens at the panel level.
 */
export const PlayerAnalyticsView: React.FC<PlayerAnalyticsViewProps> = ({
  onBack,
}) => {
  const { selectedPlayer, comparisonPlayer, activePanels } =
    usePlayerAnalyticsStore(
      useShallow((s) => ({
        selectedPlayer: s.selectedPlayer,
        comparisonPlayer: s.comparisonPlayer,
        activePanels: s.activePanels,
      })),
    );
  const setComparison = usePlayerAnalyticsStore((s) => s.setComparison);
  const togglePanel = usePlayerAnalyticsStore((s) => s.togglePanel);
  const openSearch = useSearchStore((s) => s.open);

  const result = usePlayerAnalytics(selectedPlayer, comparisonPlayer);

  useEffect(() => {
    if (!selectedPlayer) onBack();
  }, [selectedPlayer, onBack]);

  const panelItems = useMemo(() => {
    if (!selectedPlayer) return [];

    const items = [
      {
        key: 'weekly' as const,
        active: activePanels.has('weekly'),
        volume: result.volumes.weekly,
        kind: 'full' as const,
        node: (
          <WeeklyTrendPanel
            data={result.weekly.data}
            isLoading={result.weekly.isLoading}
            error={result.weekly.error}
          />
        ),
      },
      {
        key: 'opponent' as const,
        active: activePanels.has('opponent'),
        volume: result.volumes.opponent,
        kind: 'full' as const,
        node: (
          <VsOpponentPanel
            data={result.vsOpponent.data}
            isLoading={result.vsOpponent.isLoading}
            error={result.vsOpponent.error}
          />
        ),
      },
      {
        key: 'stadium' as const,
        active: activePanels.has('stadium'),
        volume: result.volumes.stadium,
        kind: 'full' as const,
        node: (
          <StadiumPanel
            data={result.stadium.data}
            isLoading={result.stadium.isLoading}
            error={result.stadium.error}
          />
        ),
      },
      {
        key: 'surface' as const,
        active: activePanels.has('surface'),
        volume: result.volumes.surface,
        kind: 'half' as const,
        node: (
          <SurfacePanel
            data={result.surface.data}
            isLoading={result.surface.isLoading}
            error={result.surface.error}
          />
        ),
      },
      {
        key: 'metadata' as const,
        active: activePanels.has('metadata'),
        volume: result.volumes.metadata,
        kind: 'half' as const,
        node: (
          <MetadataOverlayPanel
            data={result.metadata.data}
            isLoading={result.metadata.isLoading}
            error={result.metadata.error}
          />
        ),
      },
    ];

    return items
      .filter((i) => i.active)
      .sort((a, b) => {
        if (b.volume !== a.volume) return b.volume - a.volume;
        const ar = result.recency[a.key];
        const br = result.recency[b.key];
        if (br !== ar) return br - ar;
        return 0;
      });
  }, [selectedPlayer, activePanels, result]);

  if (!selectedPlayer) return null;

  const halfKeys = panelItems
    .filter((p) => p.kind === 'half')
    .map((p) => p.key) as Array<'surface' | 'metadata'>;
  const lastHalfPanelKey =
    halfKeys.length % 2 === 1 ? halfKeys[halfKeys.length - 1] : null;

  return (
    <div className="space-y-4">
      <AnalyticsHeader
        player={selectedPlayer}
        comparison={comparisonPlayer}
        activePanels={activePanels}
        onBack={onBack}
        onOpenComparison={openSearch}
        onClearComparison={() => setComparison(null)}
        onTogglePanel={togglePanel}
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {panelItems.map((p) => {
          const span =
            p.kind === 'full'
              ? 'xl:col-span-2 min-w-0'
              : lastHalfPanelKey === p.key
                ? 'xl:col-span-2 min-w-0'
                : 'min-w-0';
          return (
            <div key={p.key} className={span}>
              {p.node}
            </div>
          );
        })}
      </div>
    </div>
  );
};
