import React, { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { BarChart3, Layers, Sparkles } from 'lucide-react';

import { ApiError, RankingsApi } from '../../api/rankingsApi';
import { useToast } from '../../contexts/ToastContext';
import type { Ranking } from '../../models/Ranking';

type SplitPayload = {
  year: number;
  filters: {
    opponent?: string | null;
    indoor_outdoor?: string | null;
    surface_type?: string | null;
    elevation_band?: string | null;
  };
  baseline: {
    games: number;
    avg_fpts_ppr: number | null;
    avg_scrimmage_yds: number | null;
  };
  conditional: {
    games: number;
    avg_fpts_ppr: number | null;
    avg_scrimmage_yds: number | null;
  };
  delta_pct: {
    fpts_ppr: number | null;
    scrimmage_yds: number | null;
  };
};

function fmtPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(1)}%`;
}

function fmtNum(v: number | null | undefined, frac = 2): string {
  if (v == null || Number.isNaN(v)) return '—';
  return v.toLocaleString(undefined, { minimumFractionDigits: frac, maximumFractionDigits: frac });
}

interface SituationalDashboardProps {
  position: string;
  year: string;
  roster: Ranking[];
}

export const SituationalDashboard: React.FC<SituationalDashboardProps> = ({
  position,
  year,
  roster,
}) => {
  const { showError } = useToast();
  const [playerId, setPlayerId] = useState('');
  const [opponent, setOpponent] = useState('');
  const [indoorOutdoor, setIndoorOutdoor] = useState('');
  const [surface, setSurface] = useState('');
  const [elevation, setElevation] = useState('');

  const rosterSorted = useMemo(() => {
    return [...roster].sort((a, b) =>
      (a.player_name || '').localeCompare(b.player_name || '', undefined, { sensitivity: 'base' }),
    );
  }, [roster]);

  const { data: facets, isLoading: facetsLoading } = useQuery({
    queryKey: ['facets', position, playerId, year],
    queryFn: ({ signal }) => RankingsApi.fetchPlayerFacets(position, playerId, year, signal),
    enabled: Boolean(position && playerId && year),
  });

  const { data: surfaceImpact, isLoading: impactLoading } = useQuery({
    queryKey: ['impact', 'surface', position, playerId, year],
    queryFn: ({ signal }) => RankingsApi.fetchPlayerImpact(position, playerId, 'surface', year, signal),
    enabled: Boolean(position && playerId && year),
  });

  const splitMutation = useMutation({
    mutationFn: async () => {
      const raw = await RankingsApi.fetchPlayerSplits(position, playerId, year, {
        opponent: opponent || undefined,
        indoor_outdoor: indoorOutdoor || undefined,
        surface_type: surface || undefined,
        elevation_band: elevation || undefined,
      });
      return raw as SplitPayload;
    },
    onError: (err: unknown) => {
      const e = err instanceof ApiError ? err : err instanceof Error ? err : new Error(String(err));
      const code = e instanceof ApiError ? e.code : undefined;
      showError(e.message, code);
    },
  });

  const hasFilter =
    Boolean(opponent) || Boolean(indoorOutdoor) || Boolean(surface) || Boolean(elevation);

  const onAnalyze = () => {
    if (!playerId || !year) {
      showError('Select a player and season first.');
      return;
    }
    if (!hasFilter) {
      showError('Choose at least one condition (matchup, stadium, surface, or elevation).');
      return;
    }
    splitMutation.mutate();
  };

  const split = splitMutation.data;

  return (
    <motion.div
      layout
      className="space-y-6"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="rounded-2xl border border-white/[0.08] bg-[rgba(15,23,42,0.45)] p-6 shadow-xl backdrop-blur-xl">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-slate-500">Situational intelligence</p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-white sm:text-2xl">
              Conditional <span className="text-sky-400">analysis</span>
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
              Stack matchup, stadium type, surface, and elevation filters. DuckDB aggregates weekly logs into baseline vs.
              filtered splits — ideal for spotting indoor turf spikes or altitude effects.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
            <Sparkles className="h-4 w-4 text-amber-400" aria-hidden />
            <span className="tabular-nums">{year}</span>
            <span className="text-slate-600">·</span>
            <span className="uppercase tracking-wide text-slate-500">{position}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Player</label>
            <select
              value={playerId}
              onChange={(e) => {
                setPlayerId(e.target.value);
                setOpponent('');
                setIndoorOutdoor('');
                setSurface('');
                setElevation('');
                splitMutation.reset();
              }}
              className="glass-select w-full text-sm"
            >
              <option value="">Select a player from the current leaderboard</option>
              {rosterSorted.map((r) => (
                <option key={r.player_id} value={r.player_id}>
                  {r.player_name} · {r.team ?? '—'}
                </option>
              ))}
            </select>
            {roster.length === 0 ? (
              <p className="text-xs text-slate-500">Load rankings to populate this roster.</p>
            ) : null}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Matchup</label>
              <select
                value={opponent}
                onChange={(e) => setOpponent(e.target.value)}
                disabled={!playerId || facetsLoading}
                className="glass-select mt-1 w-full text-sm disabled:opacity-50"
              >
                <option value="">Any opponent</option>
                {(facets?.opponents ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Stadium type</label>
              <select
                value={indoorOutdoor}
                onChange={(e) => setIndoorOutdoor(e.target.value)}
                disabled={!playerId || facetsLoading}
                className="glass-select mt-1 w-full text-sm disabled:opacity-50"
              >
                <option value="">Indoor / Outdoor</option>
                {(facets?.indoor_outdoor ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Surface</label>
              <select
                value={surface}
                onChange={(e) => setSurface(e.target.value)}
                disabled={!playerId || facetsLoading}
                className="glass-select mt-1 w-full text-sm disabled:opacity-50"
              >
                <option value="">Turf / Grass</option>
                {(facets?.surface_type ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">Elevation</label>
              <select
                value={elevation}
                onChange={(e) => setElevation(e.target.value)}
                disabled={!playerId || facetsLoading}
                className="glass-select mt-1 w-full text-sm disabled:opacity-50"
              >
                <option value="">Low / Med / High</option>
                {(facets?.elevation_band ?? []).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onAnalyze}
            disabled={!playerId || splitMutation.isPending}
            className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-2.5 text-sm font-bold uppercase tracking-wide text-white shadow-lg shadow-sky-500/25 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Layers size={16} aria-hidden />
            {splitMutation.isPending ? 'Computing…' : 'Run split analysis'}
          </button>
          {facetsLoading && playerId ? (
            <span className="text-xs text-slate-500">Loading filter vocabulary…</span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="rounded-2xl border border-white/[0.08] bg-[rgba(2,6,23,0.55)] p-6 backdrop-blur-xl">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-sky-400" aria-hidden />
            <h3 className="text-sm font-bold uppercase tracking-widest text-slate-300">Surface splits (season)</h3>
          </div>
          {!playerId ? (
            <p className="text-sm text-slate-500">Pick a player to load turf vs. grass tendencies for {year}.</p>
          ) : impactLoading ? (
            <div className="space-y-2">
              <div className="h-3 w-1/3 animate-pulse rounded bg-slate-700" />
              <div className="h-20 animate-pulse rounded-lg bg-slate-800/80" />
            </div>
          ) : surfaceImpact && surfaceImpact.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
              <table className="w-full min-w-[320px] text-left text-[13px]">
                <thead>
                  <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-500">
                    <th className="px-3 py-2 font-semibold">Surface</th>
                    <th className="px-3 py-2 text-right font-semibold">PPR / gm</th>
                    <th className="px-3 py-2 text-right font-semibold">Games</th>
                  </tr>
                </thead>
                <tbody>
                  {surfaceImpact.map((row) => (
                    <tr key={String(row.metric_label)} className="border-b border-white/[0.04]">
                      <td className="px-3 py-2.5 font-medium text-slate-200">{String(row.metric_label)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-sky-200">{fmtNum(row.avg_fpts_ppr)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-slate-400">
                        {fmtNum(row.games_played, 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No enriched surface metadata for this sample.</p>
          )}
        </div>

        <div className="rounded-2xl border border-white/[0.08] bg-[rgba(15,23,42,0.55)] p-6 backdrop-blur-xl">
          <h3 className="mb-2 text-sm font-bold uppercase tracking-widest text-slate-300">Filtered vs. baseline</h3>
          <p className="mb-4 text-xs leading-relaxed text-slate-500">
            Averages compare the full {year} slate to games matching <span className="text-slate-300">all</span> active
            conditions simultaneously.
          </p>
          {!split ? (
            <div className="flex min-h-[140px] flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] bg-white/[0.02] px-4 text-center">
              <p className="text-sm text-slate-500">
                Run split analysis to see delta on PPR and scrimmage yards (pass + rush where available).
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Baseline games</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-white">{split.baseline.games}</p>
                </div>
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Filtered games</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums text-white">{split.conditional.games}</p>
                </div>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Δ PPR / game</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-sky-200">{fmtPct(split.delta_pct.fpts_ppr)}</p>
                  <p className="mt-1 text-[11px] tabular-nums text-slate-500">
                    {fmtNum(split.baseline.avg_fpts_ppr)} → {fmtNum(split.conditional.avg_fpts_ppr)}
                  </p>
                </div>
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-3 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Δ Scrimmage YDS / gm</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-emerald-200">
                    {fmtPct(split.delta_pct.scrimmage_yds)}
                  </p>
                  <p className="mt-1 text-[11px] tabular-nums text-slate-500">
                    {fmtNum(split.baseline.avg_scrimmage_yds)} → {fmtNum(split.conditional.avg_scrimmage_yds)}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
