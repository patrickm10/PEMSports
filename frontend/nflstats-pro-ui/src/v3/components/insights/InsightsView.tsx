import type { InsightPosition } from '../../../api/insightsTypes';
import {
  useInsightsLeaderboard,
  useInsightsPlayerDetail,
} from '../../../hooks/useInsights';
import { useInsightsStore } from '../../../stores/insightsStore';
import { ContextSelector } from './ContextSelector';
import { InsightsLeaderboard } from './InsightsLeaderboard';
import { InsightsPlayerDetail } from './InsightsPlayerDetail';
import { PositionTabs } from './PositionTabs';

interface InsightsViewProps {
  selectedYear: string;
  selectedWeek: string;
  viewMode: 'season' | 'weekly';
}

const POSITION_LABELS: Record<string, string> = {
  qb: 'QB',
  rb: 'RB',
  wr: 'WR',
  te: 'TE',
};

export function InsightsView({ selectedYear, selectedWeek, viewMode }: InsightsViewProps) {
  const position = useInsightsStore((s) => s.position);
  const context = useInsightsStore((s) => s.context);
  const contextValue = useInsightsStore((s) => s.contextValue);
  const selectedPlayerId = useInsightsStore((s) => s.selectedPlayerId);
  const selectedPlayerPosition = useInsightsStore((s) => s.selectedPlayerPosition);
  const setPosition = useInsightsStore((s) => s.setPosition);
  const selectPlayer = useInsightsStore((s) => s.selectPlayer);

  const filters = { year: selectedYear, week: selectedWeek, viewMode };

  const {
    data: leaderboard,
    isLoading: leaderboardLoading,
    isError: leaderboardError,
    refetch: refetchLeaderboard,
  } = useInsightsLeaderboard(filters);
  const {
    data: playerDetail,
    isLoading: detailLoading,
    isError: detailError,
    refetch: refetchDetail,
  } = useInsightsPlayerDetail(selectedPlayerId, selectedPlayerPosition, filters);

  const contextLabel = `${context.replace('_', ' ')}: ${contextValue || '—'}`;

  const handleSelect = (row: {
    player_id: string;
    position: string;
    player_name: string | null;
  }) => {
    const pos = row.position.toLowerCase() as Exclude<InsightPosition, 'all'>;
    selectPlayer(row.player_id, pos);
  };

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      <p className="text-slate-400 text-sm">
        Relative performance vs each player&apos;s season baseline in specific contexts
      </p>

      <PositionTabs active={position} onChange={setPosition} />

      <ContextSelector year={selectedYear} />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="space-y-4">
          {leaderboardError || leaderboardLoading || position !== 'all' || !leaderboard?.groups ? (
            <InsightsLeaderboard
              title={`Top ${POSITION_LABELS[position] ?? position.toUpperCase()} — ${contextValue || '…'}`}
              rows={leaderboard?.insights ?? []}
              selectedPlayerId={selectedPlayerId}
              onSelect={handleSelect}
              isLoading={leaderboardLoading}
              isError={leaderboardError}
              onRetry={() => void refetchLeaderboard()}
            />
          ) : (
            leaderboard.groups.map((group) => (
              <InsightsLeaderboard
                key={group.position}
                title={`Top ${POSITION_LABELS[group.position] ?? group.position.toUpperCase()} — ${contextValue}`}
                rows={group.insights}
                selectedPlayerId={selectedPlayerId}
                onSelect={handleSelect}
              />
            ))
          )}
        </div>

        <InsightsPlayerDetail
          detail={playerDetail}
          isLoading={detailLoading}
          isError={detailError}
          onRetry={() => void refetchDetail()}
          contextLabel={contextLabel}
        />
      </div>
    </div>
  );
}
