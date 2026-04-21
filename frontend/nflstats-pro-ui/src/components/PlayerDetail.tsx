import React, { useEffect, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { X } from 'lucide-react';

import type { Ranking } from '../models/Ranking';
import { isWeeklyRanking } from '../models/Ranking';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import { PlayerAvatar } from './VirtualizedGrid';
import { clsx } from 'clsx';

/** Prefer position-scored TDs; season payload may omit some keys. */
export function headlineTdTotal(position: string, season: Record<string, unknown>): number {
  const p = position.toLowerCase();
  if (p === 'dst') {
    return (
      (Number(season.def_td) || 0) +
      (Number(season.st_td) || 0) +
      (Number(season.safety) || 0)
    );
  }
  const rushTd = Number(season.rush_td ?? season.r_td) || 0;
  const scoringTd = Number(season.td) || 0;
  return scoringTd + rushTd;
}

const LOG_STAT_KEYS = [
  'cmp',
  'att',
  'int',
  'yds',
  'rush_yds',
  'tgt',
  'rec',
  'td',
  'rush_td',
  'r_td',
] as const;

interface PlayerDetailProps {
  playerId: string;
  position: string;
  year: string;
  snapshot: Ranking;
  onClose: () => void;
}

function fmtNum(v: unknown, frac = 1): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = typeof v === 'number' ? v : Number(v);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString(undefined, {
    minimumFractionDigits: frac,
    maximumFractionDigits: frac,
  });
}

function weatherLine(row: Record<string, unknown>): string {
  const parts: string[] = [];
  const t = row.temp;
  const w = row.wind;
  const h = row.humidity;
  if (typeof t === 'number' && Number.isFinite(t)) parts.push(`${Math.round(t)}°F`);
  if (typeof w === 'number' && Number.isFinite(w)) parts.push(`W ${w.toFixed(0)}`);
  if (typeof h === 'number' && Number.isFinite(h)) parts.push(`${Math.round(h)}% hum`);
  return parts.length ? parts.join(' · ') : '—';
}

export const PlayerDetail: React.FC<PlayerDetailProps> = ({
  playerId,
  position,
  year,
  snapshot,
  onClose,
}) => {
  const overlayRef = useRef<HTMLDivElement>(null);
  const snapshotRowIsWeekly = isWeeklyRanking(snapshot);

  const { data, isLoading, isError, error, refetch } = usePlayerProfile(
    playerId,
    year,
    position,
    true,
  );

  const season = data?.season as Record<string, unknown> | undefined;
  const weekly = (data?.weekly_games ?? []) as Record<string, unknown>[];
  const seasonHistory = (data?.season_history ?? []) as Record<string, unknown>[];

  const displayName =
    (season?.player_name as string) ?? snapshot.player_name ?? '—';
  const displayTeam = (season?.team as string) ?? snapshot.team ?? '—';
  const displayRank =
    (season?.rank as number | undefined) ??
    (!snapshotRowIsWeekly ? (snapshot.rank as number | undefined) : undefined);

  const logStatKeys = useMemo(() => {
    const first = weekly[0];
    if (!first) return [] as string[];
    return LOG_STAT_KEYS.filter((k) => first[k] != null && first[k] !== '');
  }, [weekly]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const headerRow = season ?? (snapshot as unknown as Record<string, unknown>);
  const tdHeadline = season
    ? headlineTdTotal(position, season)
    : headlineTdTotal(position, snapshot as unknown as Record<string, unknown>);

  /** Weekly grid rows show single-game / week-rank stats — hide misleading season totals until API returns. */
  const highlightPpr =
    season != null
      ? fmtNum(season.fpts_ppr)
      : snapshotRowIsWeekly && !season
        ? '—'
        : fmtNum(snapshot.fpts_ppr);
  const highlightPpg =
    season != null
      ? fmtNum(season.fpts_ppr_per_game)
      : snapshotRowIsWeekly && !season
        ? '—'
        : fmtNum(snapshot.fpts_ppr_per_game);
  const highlightTd =
    season != null ? fmtNum(headlineTdTotal(position, season), 0) : snapshotRowIsWeekly && !season
      ? '—'
      : fmtNum(tdHeadline, 0);

  return (
    <motion.div
      className="modal-overlay !z-[80] px-3 py-6 sm:px-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="player-detail-title"
      ref={overlayRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <motion.div
        role="document"
        className={clsx(
          'modal-content mx-auto flex w-full max-w-[min(1400px,98vw)] flex-col overflow-hidden',
          'max-h-[min(92vh,1100px)] min-h-[min(48vh,520px)]',
          'glass-panel rounded-2xl border border-white/10 shadow-2xl',
          'bg-[rgba(15,23,42,0.78)] backdrop-blur-xl',
        )}
        initial={{ opacity: 0, scale: 0.94, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 12 }}
        transition={{ type: 'spring', stiffness: 440, damping: 30, mass: 0.82 }}
      >
        <button
          type="button"
          className="btn-close absolute right-3 top-3 z-10"
          onClick={onClose}
          aria-label="Close detail panel"
        >
          <X size={22} />
        </button>

        <div className="shrink-0 border-b border-white/[0.08] px-5 pt-10 pb-5 sm:px-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <PlayerAvatar
              row={headerRow}
              imgClassName="h-24 w-24 rounded-full object-cover ring-2 ring-white/10 bg-slate-800 shadow-lg sm:h-[5.5rem] sm:w-[5.5rem]"
            />
            <div className="min-w-0 flex-1">
              <h2
                id="player-detail-title"
                className="text-2xl font-bold tracking-tight text-white sm:text-3xl truncate"
              >
                {displayName}
              </h2>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                <span className="rounded-md bg-sky-500/15 px-2 py-0.5 text-sky-300 ring-1 ring-sky-400/25">
                  Season rank #
                  {displayRank != null ? String(Math.floor(Number(displayRank))) : isLoading ? '…' : '—'}
                </span>
                <span className="rounded-md bg-white/[0.06] px-2 py-0.5 text-slate-200 ring-1 ring-white/[0.08]">
                  {position.toUpperCase()}
                </span>
                <span className="rounded-md bg-white/[0.06] px-2 py-0.5 text-slate-200 ring-1 ring-white/[0.08]">
                  {(displayTeam ?? '—').toString().replace('_', ' ')}
                </span>
                <span className="text-slate-500 normal-case font-medium tracking-normal">{year} Season</span>
              </div>
            </div>
          </div>

          <div
            className={clsx(
              'mt-6 grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-3',
              snapshotRowIsWeekly && isLoading && !season && 'animate-pulse opacity-80',
            )}
          >
            {[
              { label: 'Total PPR', value: highlightPpr },
              { label: 'Avg PPG', value: highlightPpg },
              { label: 'TD Total', value: highlightTd },
            ].map((m) => (
              <div
                key={m.label}
                className="rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-4 text-center min-h-[4.25rem] flex flex-col justify-center"
              >
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  {m.label}
                </p>
                <p className="mt-1 text-xl font-bold tabular-nums text-white sm:text-2xl break-all">
                  {m.value}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:px-8 sm:py-5">
          {isLoading && (
            <div className="space-y-2 px-2 py-4">
              <div className="h-3 w-1/3 animate-pulse rounded bg-slate-700" />
              <div className="h-24 animate-pulse rounded-lg bg-slate-800/80" />
              <div className="h-24 animate-pulse rounded-lg bg-slate-800/80" />
            </div>
          )}

          {isError && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 px-4 py-3 text-sm text-rose-100">
              <p className="font-semibold">Could not load profile</p>
              <p className="mt-1 text-rose-200/90">{error?.message ?? 'Request failed'}</p>
              <button
                type="button"
                onClick={() => refetch()}
                className="mt-3 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/15"
              >
                Retry
              </button>
            </div>
          )}

          {!isLoading && !isError && seasonHistory.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Season history
              </h3>
              <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
                <table className="w-full min-w-[480px] text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-500">
                      <th className="whitespace-nowrap px-3 py-2 font-semibold">Year</th>
                      <th className="whitespace-nowrap px-3 py-2 font-semibold">Rank</th>
                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">PPR</th>
                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">PPR/G</th>
                      <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">Games</th>
                    </tr>
                  </thead>
                  <tbody>
                    {seasonHistory.map((row, i) => {
                      const yr = row.year;
                      return (
                        <tr
                          key={`${String(yr)}-${i}`}
                          className={clsx(
                            'border-b border-white/[0.04]',
                            Number(yr) === Number(year) && 'bg-sky-500/10',
                          )}
                        >
                          <td className="whitespace-nowrap px-3 py-2.5 font-medium tabular-nums text-slate-200">
                            {yr != null ? String(Math.floor(Number(yr))) : '—'}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-slate-300 tabular-nums">
                            {fmtNum(row.rank, 0)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-right tabular-nums text-slate-200">
                            {fmtNum(row.fpts_ppr)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-right tabular-nums text-slate-400">
                            {fmtNum(row.fpts_ppr_per_game)}
                          </td>
                          <td className="whitespace-nowrap px-3 py-2.5 text-right tabular-nums text-slate-400">
                            {fmtNum(row.games_played, 0)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!isLoading && !isError && weekly.length === 0 && (
            <p className="px-2 py-6 text-center text-sm text-slate-400">
              No weekly game rows for this season.
            </p>
          )}

          {!isLoading && !isError && weekly.length > 0 && (
            <div>
              <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                Game log ({year})
              </h3>
              <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
                <table className="w-full min-w-[640px] table-fixed text-left text-[13px]">
                  <colgroup>
                    <col className="w-[3rem]" />
                    <col className="w-[4rem]" />
                    <col className="w-[min(10rem,12%)]" />
                    <col />
                    <col className="w-[4rem]" />
                    <col className="w-[4rem]" />
                  </colgroup>
                  <thead>
                    <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-500">
                      <th className="px-2 py-2 font-semibold">Wk</th>
                      <th className="px-2 py-2 font-semibold">Opp</th>
                      <th className="px-2 py-2 font-semibold">Weather</th>
                      <th className="px-2 py-2 font-semibold">Stats</th>
                      <th className="px-2 py-2 text-right font-semibold">FP</th>
                      <th className="px-2 py-2 text-right font-semibold">PPR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weekly.map((row, i) => {
                      const wk = row.week;
                      const statBits =
                        logStatKeys.length > 0
                          ? logStatKeys
                              .map((k) => `${k.replace(/_/g, ' ')} ${fmtNum(row[k])}`)
                              .join(' · ')
                          : '—';
                      return (
                        <tr key={`${String(wk ?? i)}-${i}`} className="border-b border-white/[0.04] hover:bg-white/[0.03]">
                          <td className="whitespace-nowrap px-2 py-2.5 align-top text-slate-300 tabular-nums">
                            {wk != null ? String(Math.floor(Number(wk))) : '—'}
                          </td>
                          <td className="whitespace-nowrap px-2 py-2.5 align-top text-slate-200">
                            {row.opponent != null ? String(row.opponent) : '—'}
                          </td>
                          <td className="px-2 py-2.5 align-top text-[11px] leading-snug text-slate-400 break-words">
                            {weatherLine(row)}
                          </td>
                          <td className="min-w-0 px-2 py-2.5 align-top text-[11px] leading-relaxed text-slate-400 break-words">
                            {statBits}
                          </td>
                          <td className="whitespace-nowrap px-2 py-2.5 align-top text-right font-medium tabular-nums text-slate-300">
                            {fmtNum(row.fpts)}
                          </td>
                          <td className="whitespace-nowrap px-2 py-2.5 align-top text-right font-semibold tabular-nums text-sky-300">
                            {fmtNum(row.fpts_ppr)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};
