import { useMemo } from 'react';
import { toInsightsTimeSeriesChartModel } from '../../../api/normalizers';
import type { InsightsPlayerDetailResponse } from '../../../api/insightsTypes';
import { MetricLineChart } from '../../../components/charts/MetricLineChart';

interface InsightsPlayerDetailProps {
  detail: InsightsPlayerDetailResponse | undefined;
  isLoading: boolean;
  contextLabel: string;
}

function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function InsightsPlayerDetail({
  detail,
  isLoading,
  contextLabel,
}: InsightsPlayerDetailProps) {
  const chartModel = useMemo(
    () => (detail ? toInsightsTimeSeriesChartModel(detail) : null),
    [detail],
  );

  if (isLoading) {
    return (
      <div className="glass-card rounded-xl p-6 text-slate-400 text-sm animate-pulse">
        Loading player history…
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="glass-card rounded-xl p-6 text-slate-500 text-sm">
        Select a player from the leaderboard to view weekly history.
      </div>
    );
  }

  const summary = detail.summary;
  const contextObs = detail.observations.filter((o) => o.in_context);

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-4">
        <h3 className="text-base font-semibold text-white">
          {summary.player_name ?? 'Player'}
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          {contextLabel} · {summary.sample_size} context games ·{' '}
          {summary.sample_strength ?? '—'} sample strength
        </p>
        <p className="text-sm text-slate-300 mt-2">
          Relative change:{' '}
          <span
            className={
              (summary.relative_delta_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }
          >
            {formatPct(summary.relative_delta_pct)}
          </span>
        </p>
      </div>

      <MetricLineChart
        data={chartModel}
        title="Weekly performance vs season baseline"
        subtitle="Leave-one-out season baseline per week"
        height={280}
        isLoading={isLoading}
        emptyMessage="No weekly observations for this filter."
      />

      <div className="glass-card rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-white/[0.06]">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Context games
          </h4>
        </div>
        <div className="overflow-x-auto max-h-64 overflow-y-auto custom-scrollbar">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900/95">
              <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                <th className="px-3 py-2">Season</th>
                <th className="px-2 py-2">Wk</th>
                <th className="px-2 py-2">Opp</th>
                <th className="px-2 py-2">Surface</th>
                <th className="px-2 py-2">H/A</th>
                <th className="px-2 py-2 text-right">FPts</th>
                <th className="px-2 py-2 text-right">Baseline</th>
                <th className="px-3 py-2 text-right">Rel.</th>
              </tr>
            </thead>
            <tbody>
              {contextObs.map((o) => (
                <tr key={`${o.season}-${o.week}`} className="border-t border-white/[0.04]">
                  <td className="px-3 py-1.5 text-slate-300">{o.season}</td>
                  <td className="px-2 py-1.5 text-slate-300">{o.week}</td>
                  <td className="px-2 py-1.5 text-slate-400">{o.opponent ?? '—'}</td>
                  <td className="px-2 py-1.5 text-slate-400">{o.surface_type ?? '—'}</td>
                  <td className="px-2 py-1.5 text-slate-400">{o.home_away ?? '—'}</td>
                  <td className="px-2 py-1.5 text-right text-slate-200">
                    {o.fantasy_points?.toFixed(1) ?? '—'}
                  </td>
                  <td className="px-2 py-1.5 text-right text-slate-400">
                    {o.season_baseline?.toFixed(1) ?? '—'}
                  </td>
                  <td className="px-3 py-1.5 text-right text-slate-300">
                    {formatPct(o.relative_change_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
