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

  const { data: leaderboard, isLoading: leaderboardLoading } = useInsightsLeaderboard(filters);
  const { data: playerDetail, isLoading: detailLoading } = useInsightsPlayerDetail(
    selectedPlayerId,
    selectedPlayerPosition,
    filters,
  );

  const contextLabel = `${context.replace('_', ' ')}: ${contextValue}`;

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
      <header>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
          PEM <span className="text-sky-400">Insights</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Relative performance vs each player&apos;s season baseline in specific contexts
        </p>
      </header>

      <PositionTabs active={position} onChange={setPosition} />

      <ContextSelector year={selectedYear} />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <div className="space-y-4">
          {position === 'all' && leaderboard?.groups ? (
            leaderboard.groups.map((group) => (
              <InsightsLeaderboard
                key={group.position}
                title={`Top ${POSITION_LABELS[group.position] ?? group.position.toUpperCase()} — ${contextValue}`}
                rows={group.insights}
                selectedPlayerId={selectedPlayerId}
                onSelect={handleSelect}
                isLoading={leaderboardLoading}
              />
            ))
          ) : (
            <InsightsLeaderboard
              title={`Top ${POSITION_LABELS[position] ?? position.toUpperCase()} — ${contextValue}`}
              rows={leaderboard?.insights ?? []}
              selectedPlayerId={selectedPlayerId}
              onSelect={handleSelect}
              isLoading={leaderboardLoading}
            />
          )}
        </div>

        <InsightsPlayerDetail
          detail={playerDetail}
          isLoading={detailLoading}
          contextLabel={contextLabel}
        />
      </div>
    </div>
  );
}
