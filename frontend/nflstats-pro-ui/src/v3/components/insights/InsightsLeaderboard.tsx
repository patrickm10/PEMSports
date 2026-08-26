import type { InsightRow } from '../../../api/insightsTypes';

function formatPct(value: number | null): string {
  if (value === null || value === undefined) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function formatNum(value: number | null): string {
  if (value === null || value === undefined) return '—';
  return value.toFixed(1);
}

interface InsightsLeaderboardProps {
  title: string;
  rows: InsightRow[];
  selectedPlayerId: string | null;
  onSelect: (row: InsightRow) => void;
  isLoading?: boolean;
}

export function InsightsLeaderboard({
  title,
  rows,
  selectedPlayerId,
  onSelect,
  isLoading,
}: InsightsLeaderboardProps) {
  if (isLoading) {
    return (
      <div className="glass-card rounded-xl p-6 text-slate-400 text-sm animate-pulse">
        Loading insights…
      </div>
    );
  }

  if (!rows.length) {
    return (
      <div className="glass-card rounded-xl p-6 text-slate-400 text-sm">
        No insights match these filters. Try a different context or season.
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <p className="text-[10px] text-slate-500 mt-1">
          Ranked by sample-weighted insight score (relative change × sample strength)
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500 border-b border-white/[0.06]">
              <th className="px-4 py-2 font-semibold">Player</th>
              <th className="px-3 py-2 font-semibold text-right">Games</th>
              <th className="px-3 py-2 font-semibold text-right">Baseline</th>
              <th className="px-3 py-2 font-semibold text-right">Context Avg</th>
              <th className="px-3 py-2 font-semibold text-right">Rel. Change</th>
              <th className="px-3 py-2 font-semibold text-right">Strength</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const active = row.player_id === selectedPlayerId;
              return (
                <tr
                  key={row.player_id}
                  onClick={() => onSelect(row)}
                  className={`cursor-pointer border-b border-white/[0.04] transition-colors ${
                    active ? 'bg-sky-500/10' : 'hover:bg-white/[0.03]'
                  }`}
                >
                  <td className="px-4 py-2.5">
                    <div className="font-medium text-slate-100">{row.player_name ?? '—'}</div>
                    <div className="text-xs text-slate-500">{row.team ?? ''}</div>
                  </td>
                  <td className="px-3 py-2.5 text-right text-slate-300">{row.sample_size}</td>
                  <td className="px-3 py-2.5 text-right text-slate-300">
                    {formatNum(row.baseline_value)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-slate-300">
                    {formatNum(row.context_average)}
                  </td>
                  <td
                    className={`px-3 py-2.5 text-right font-semibold ${
                      (row.relative_delta_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {formatPct(row.relative_delta_pct)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-slate-400 text-xs">
                    {row.sample_strength}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
