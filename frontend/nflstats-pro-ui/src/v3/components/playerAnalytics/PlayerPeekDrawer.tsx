import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, X } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { Ranking } from '../../../models/Ranking';
import type { PlayerRef } from '../../../stores/types';
import type {
  CategoricalChartModel,
  MetadataOverlayModel,
  TimeSeriesChartModel,
} from '../../../components/charts/contract';
import {
  PUBLIC_DEFAULT_PLAYER_IMG,
  staticAssetUrl,
} from '../../../utils/backendOrigin';
import { WeeklyTrendPanel } from './panels/WeeklyTrendPanel';

const tw = (...c: Array<string | false | null | undefined>) => twMerge(clsx(c));

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function resolveHeadshot(headshot: string | null | undefined): string {
  if (!headshot) return PUBLIC_DEFAULT_PLAYER_IMG;
  if (headshot.startsWith('http')) return headshot;
  return staticAssetUrl(headshot);
}

function formatStat(value: unknown, digits = 1): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function numericOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

interface SplitBarProps {
  label: string;
  value: number | null;
  max: number;
  tone?: 'sky' | 'green';
}

const SplitBar: React.FC<SplitBarProps> = ({
  label,
  value,
  max,
  tone = 'sky',
}) => {
  const width =
    value === null || max <= 0 ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs font-medium text-slate-300">
        <span>{label}</span>
        <span className="tabular-nums">
          {value === null ? '—' : `${formatStat(value, 1)} per game`}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-sm bg-white/[0.06]">
        <div
          className={tw(
            'h-1.5 rounded-sm',
            tone === 'green' ? 'bg-emerald-500' : 'bg-sky-400',
          )}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
};

interface PlayerPeekDrawerProps {
  isOpen: boolean;
  player: PlayerRef | null;
  rankingRow: Ranking | null;
  weekly: {
    data: TimeSeriesChartModel | null;
    isLoading: boolean;
    error: Error | null;
  };
  metadata: {
    data: MetadataOverlayModel | null;
    isLoading: boolean;
    error: Error | null;
  };
  surface: {
    data: CategoricalChartModel | null;
    isLoading: boolean;
    error: Error | null;
  };
  focusSerial?: number;
  onClose: () => void;
  onOpenFull: () => void;
}

/**
 * Presentational peek overlay. Receives pre-normalized analytics slices and
 * an optional rankings row for identity stats. Does not fetch or navigate.
 */
export const PlayerPeekDrawer: React.FC<PlayerPeekDrawerProps> = ({
  isOpen,
  player,
  rankingRow,
  weekly,
  metadata,
  surface,
  focusSerial = 0,
  onClose,
  onOpenFull,
}) => {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    lastFocusedRef.current = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    return () => {
      lastFocusedRef.current?.focus?.();
    };
  }, [isOpen, player?.player_id, focusSerial]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;

      const focusables = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((el) => !el.hasAttribute('disabled') && el.tabIndex !== -1);
      if (focusables.length === 0) return;

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  const fpts = rankingRow ? numericOrNull(rankingRow.fpts) : null;
  const perGame = rankingRow ? numericOrNull(rankingRow.fpts_per_game) : null;
  const yards = rankingRow ? numericOrNull(rankingRow.yds) : null;
  const tds = rankingRow ? numericOrNull(rankingRow.td) : null;
  const rank = rankingRow ? numericOrNull(rankingRow.rank) : null;
  const games = rankingRow ? numericOrNull(rankingRow.games_played) : null;

  const homePpr = metadata.data?.homeAway.home.ppr ?? null;
  const awayPpr = metadata.data?.homeAway.away.ppr ?? null;
  const haMax = Math.max(homePpr ?? 0, awayPpr ?? 0);

  const surfaceSeries = surface.data?.series[0];
  const surfacePairs =
    surface.data && surfaceSeries
      ? surface.data.categories.map((label, i) => ({
          label,
          value: surfaceSeries.values[i] ?? null,
        }))
      : [];
  const surfaceMax = surfacePairs.reduce(
    (m, p) => (p.value !== null && p.value > m ? p.value : m),
    0,
  );

  const metaLine = [
    rank !== null ? `Rank ${rank}` : null,
    player?.team ?? rankingRow?.team ?? null,
    games !== null ? `${games} games` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  const tree = (
            <AnimatePresence>
      {isOpen && player && (
        <React.Fragment key={player.player_id}>
          <motion.button
            key="pem-peek-scrim"
            type="button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[90] bg-slate-950/55"
            aria-label="Close player peek"
            onClick={onClose}
          />
          <motion.aside
            key="pem-peek-panel"
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="pem-peek-title"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-y-0 right-0 z-[91] flex w-full max-w-[520px] flex-col border-l border-white/[0.09] bg-slate-950/98 shadow-[-24px_0_60px_rgba(0,0,0,0.6)]"
          >
            <div className="flex shrink-0 items-start gap-4 border-b border-white/[0.07] px-6 py-5">
              <img
                src={resolveHeadshot(player.headshot_url)}
                alt=""
                className="h-14 w-14 shrink-0 rounded-[14px] border border-white/10 bg-slate-800 object-cover"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src =
                    PUBLIC_DEFAULT_PLAYER_IMG;
                }}
              />
              <div className="min-w-0 flex-1">
                <h2
                  id="pem-peek-title"
                  className="truncate text-xl font-bold tracking-tight text-white"
                >
                  {player.player_name}
                </h2>
                <p className="mt-1 text-xs font-medium text-slate-400">
                  {metaLine ||
                    [player.position?.toUpperCase(), player.team]
                      .filter(Boolean)
                      .join(' · ') ||
                    '—'}
                </p>
              </div>
              <button
                ref={closeRef}
                type="button"
                onClick={onClose}
                aria-label="Close player peek"
                className="rounded-lg border border-white/[0.08] p-1.5 text-slate-400 hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50"
              >
                <X size={16} />
              </button>
            </div>

            <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto px-6 py-5 custom-scrollbar">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div className="rounded-[10px] border border-sky-400/20 bg-sky-400/10 p-3">
                  <p className="text-[11px] font-medium text-sky-300">Fantasy pts</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-white">
                    {formatStat(fpts, 1)}
                  </p>
                </div>
                <div className="rounded-[10px] border border-white/[0.06] bg-white/[0.04] p-3">
                  <p className="text-[11px] font-medium text-slate-400">Per game</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-white">
                    {formatStat(perGame, 1)}
                  </p>
                </div>
                <div className="rounded-[10px] border border-white/[0.06] bg-white/[0.04] p-3">
                  <p className="text-[11px] font-medium text-slate-400">Yards</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-white">
                    {formatStat(yards, 0)}
                  </p>
                </div>
                <div className="rounded-[10px] border border-white/[0.06] bg-white/[0.04] p-3">
                  <p className="text-[11px] font-medium text-slate-400">Touchdowns</p>
                  <p className="mt-1 text-lg font-bold tabular-nums text-white">
                    {formatStat(tds, 0)}
                  </p>
                </div>
              </div>

              <WeeklyTrendPanel
                data={weekly.data}
                isLoading={weekly.isLoading}
                error={weekly.error}
                title="Weekly Points"
                subtitle="One series per season"
                height={180}
              />

              <div>
                <h3 className="mb-3 text-sm font-semibold text-white">
                  Where the points came from
                </h3>
                {metadata.isLoading || surface.isLoading ? (
                  <div className="h-24 animate-pulse rounded-xl border border-slate-800/40 bg-slate-900/40" />
                ) : metadata.error && surface.error ? (
                  <p className="text-sm text-rose-400">Unable to load split context.</p>
                ) : !metadata.data && surfacePairs.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No split context available for this player.
                  </p>
                ) : (
                  <div className="flex flex-col gap-2.5">
                    {metadata.data && (
                      <>
                        <SplitBar label="Home" value={homePpr} max={haMax} />
                        <SplitBar label="Away" value={awayPpr} max={haMax} />
                      </>
                    )}
                    {surfacePairs.map((p) => (
                      <SplitBar
                        key={p.label}
                        label={p.label}
                        value={p.value}
                        max={surfaceMax}
                        tone="green"
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex shrink-0 border-t border-white/[0.07] px-6 py-4">
              <button
                type="button"
                onClick={onOpenFull}
                className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-lg bg-sky-600 text-sm font-semibold text-white hover:bg-sky-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
              >
                Open full analytics
                <ArrowRight size={14} aria-hidden />
              </button>
            </div>
          </motion.aside>
        </React.Fragment>
      )}
    </AnimatePresence>
  );

  if (typeof document === 'undefined') return null;
  return createPortal(tree, document.body);
};
