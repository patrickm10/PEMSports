import React from 'react';
import { ArrowLeft, GitCompareArrows, X } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { AnalyticsPanel, PlayerRef } from '../../../stores/types';
import { ALL_ANALYTICS_PANELS } from '../../../stores/types';
import {
  staticAssetUrl,
  PUBLIC_DEFAULT_PLAYER_IMG,
} from '../../../utils/backendOrigin';

const cn = (...c: Array<string | false | null | undefined>) =>
  twMerge(clsx(c));

const PANEL_LABELS: Record<AnalyticsPanel, string> = {
  opponent: 'Opponent',
  stadium: 'Stadium',
  surface: 'Surface',
  weekly: 'Weekly',
  metadata: 'Context',
};

function resolveHeadshot(headshot: string | null | undefined): string {
  if (!headshot) return PUBLIC_DEFAULT_PLAYER_IMG;
  if (headshot.startsWith('http')) return headshot;
  return staticAssetUrl(headshot);
}

interface AnalyticsHeaderProps {
  player: PlayerRef;
  comparison: PlayerRef | null;
  activePanels: ReadonlySet<AnalyticsPanel>;
  onBack: () => void;
  onOpenComparison: () => void;
  onClearComparison: () => void;
  onTogglePanel: (k: AnalyticsPanel) => void;
  backButtonRef?: React.RefObject<HTMLButtonElement | null>;
}

/**
 * Strictly presentational. Receives state and dispatch handlers as props;
 * mutates nothing internally.
 */
export const AnalyticsHeader: React.FC<AnalyticsHeaderProps> = ({
  player,
  comparison,
  activePanels,
  onBack,
  onOpenComparison,
  onClearComparison,
  onTogglePanel,
  backButtonRef,
}) => {
  return (
    <section className="flex flex-col gap-4 p-5 rounded-2xl glass-card border-white/10">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex items-start gap-4 min-w-0">
          <button
            ref={backButtonRef}
            type="button"
            onClick={onBack}
            aria-label="Back to rankings"
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.05] border border-white/[0.06] shrink-0"
          >
            <ArrowLeft size={16} />
          </button>
          <img
            src={resolveHeadshot(player.headshot_url)}
            alt=""
            className="w-14 h-14 rounded-2xl bg-slate-800 object-cover border border-white/10 shrink-0"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src =
                PUBLIC_DEFAULT_PLAYER_IMG;
            }}
          />
          <div className="min-w-0">
            <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight truncate">
              {player.player_name}
            </h2>
            <div className="flex items-center gap-2 mt-1 text-xs font-medium text-slate-400">
              <span className="px-2 py-0.5 rounded-md bg-sky-500/10 border border-sky-500/30 text-sky-300">
                {player.position?.toUpperCase() ?? '—'}
              </span>
              <span>·</span>
              <span>{player.team?.toUpperCase() ?? '—'}</span>
              {comparison && (
                <>
                  <span>·</span>
                  <span className="text-amber-300">
                    vs {comparison.player_name}
                  </span>
                </>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-400 normal-case tracking-normal font-medium">
              Charts use this player&apos;s available games, not the rankings year
              or week.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {comparison ? (
            <button
              type="button"
              onClick={onClearComparison}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-amber-300 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/15"
            >
              <X size={14} /> Clear compare
            </button>
          ) : (
            <button
              type="button"
              onClick={onOpenComparison}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-slate-200 bg-white/[0.04] border border-white/[0.06] hover:bg-white/[0.08]"
            >
              <GitCompareArrows size={14} /> Compare
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-medium text-slate-500 mr-1">
          Charts
        </span>
        {ALL_ANALYTICS_PANELS.map((p) => {
          const active = activePanels.has(p);
          return (
            <button
              key={p}
              type="button"
              onClick={() => onTogglePanel(p)}
              aria-pressed={active}
              aria-label={`${active ? 'Hide' : 'Show'} ${PANEL_LABELS[p]} chart`}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-colors',
                active
                  ? 'bg-sky-500/10 border-sky-500/30 text-sky-200'
                  : 'bg-slate-950/40 border-white/[0.05] text-slate-500 hover:text-slate-300',
              )}
            >
              {PANEL_LABELS[p]}
            </button>
          );
        })}
      </div>
    </section>
  );
};
