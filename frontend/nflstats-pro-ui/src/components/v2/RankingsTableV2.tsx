import React, { useRef, useMemo, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { motion } from 'framer-motion';
import { ChevronUp, ChevronDown } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { Ranking, SortField, SortOrder } from '../../models/Ranking';
import { validateColumnSchema } from '../../utils/validateSchema';
import { Skeleton } from './Skeleton';
import en from '../../i18n/en.json';

interface RankingsTableV2Props {
  data: Ranking[];
  sortBy: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  onRowClick: (player: Ranking) => void;
  activeTab?: string;
  isLoading?: boolean;
}

const STICKY_COLUMNS: ReadonlySet<SortField> = new Set<SortField>(['rank', 'player_name']);



/** Enriched metadata columns — always present (NULL placeholders in seasonal) */
const ENRICHED_METADATA: SortField[] = [
  'opponent', 'stadium_name', 'city', 'state',
  'indoor_outdoor', 'surface_type', 'elevation',
  'temp', 'humidity', 'wind', 'game_result',
];

/** Column group definitions for grouped header row */
interface ColumnGroup {
  label: string;
  columns: SortField[];
  accent?: string;
}

function buildColumnGroups(columns: SortField[]): ColumnGroup[] {
  const groups: ColumnGroup[] = [];

  // Identity
  const identity = columns.filter(c => ['rank', 'week', 'player_name', 'team'].includes(c));
  if (identity.length) groups.push({ label: 'Identity', columns: identity, accent: 'text-slate-400' });

  // Scoring
  const scoring = columns.filter(c => ['games_played', 'fpts_ppr', 'fpts_ppr_per_game'].includes(c));
  if (scoring.length) groups.push({ label: 'Scoring', columns: scoring, accent: 'text-blue-400/70' });

  // Performance
  const knownNonPerf = new Set([...identity, ...scoring, ...ENRICHED_METADATA, 'fpts', 'season', 'position', 'player_id', 'year']);
  const perf = columns.filter(c => !knownNonPerf.has(c));
  if (perf.length) groups.push({ label: 'Performance', columns: perf, accent: 'text-emerald-400/70' });

  // Game Conditions
  const conditions = columns.filter(c => ENRICHED_METADATA.includes(c));
  if (conditions.length) groups.push({ label: 'Game Conditions', columns: conditions, accent: 'text-amber-400/60' });

  // Predictive (Weekly Alpha)
  const predictive = columns.filter(c => ['smart_projection', 'predicted_alpha'].includes(c));
  if (predictive.length) groups.push({ label: 'Alpha Analytics', columns: predictive, accent: 'text-purple-400/80' });

  return groups;
}

/** Integer columns — skip decimal formatting */
const INTEGER_COLUMNS: ReadonlySet<string> = new Set([
  'rank', 'week', 'games_played', 'td', 'targets', 'rec', 'elevation',
]);

/** Column label from i18n */
const t = en.columns as Record<string, string>;

export const RankingsTableV2: React.FC<RankingsTableV2Props> = ({
  data, sortBy, sortOrder, onSort, onRowClick, activeTab, isLoading = false,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const position = (activeTab || 'qb').toLowerCase();
  const isWeekly = data.length > 0 && 'week' in data[0];

  // ── Column Config ─────────────────────────────────────────────
  const columns = useMemo<SortField[]>(() => {
    const base: SortField[] = [
      'rank',
      ...(isWeekly ? ['week' as SortField] : []),
      'player_name', 'team',
      ...(isWeekly ? ['smart_projection' as SortField, 'predicted_alpha' as SortField] : []),
    ];
    const scoring: SortField[] = isWeekly 
      ? ['fpts_ppr', 'fpts_ppr_per_game'] 
      : ['games_played', 'fpts_ppr', 'fpts_ppr_per_game'];
    
    const enrichment = isWeekly ? ENRICHED_METADATA : [];

    const knownCols = new Set([...base, ...scoring, ...enrichment, 'fpts', 'season', 'position', 'player_id', 'year']);

    const dynamicMetrics: SortField[] = [];
    if (data.length > 0) {
      Object.keys(data[0]).forEach(key => {
        if (!knownCols.has(key)) {
          dynamicMetrics.push(key as SortField);
        }
      });
    }
    
    return [...base, ...scoring, ...dynamicMetrics, ...enrichment] as SortField[];
  }, [isWeekly, data]);

  const columnGroups = useMemo(
    () => buildColumnGroups(columns),
    [columns]
  );

  // ── Schema Validation (dev-only) ─────────────────────────────
  useEffect(() => {
    if (import.meta.env.DEV && data.length > 0) {
      console.log(`[${position.toUpperCase()} ${isWeekly ? 'weekly' : 'season'}] API keys:`, Object.keys(data[0]));
      console.log(`[${position.toUpperCase()} ${isWeekly ? 'weekly' : 'season'}] Columns config:`, columns);
    }
    validateColumnSchema(data, columns, `${position} ${isWeekly ? 'weekly' : 'season'}`, isWeekly);
  }, [data, columns, position, isWeekly]);

  // ── Grid Layout ───────────────────────────────────────────────
  const getColMin = (col: string) => {
    switch (col) {
      case 'rank': return 72;
      case 'week': return 72;
      case 'player_name': return 200;
      case 'team': return 80;
      case 'opponent': return 80;
      case 'games_played': return 72;
      case 'fpts_ppr': return 90;
      case 'fpts_ppr_per_game': return 90;
      case 'game_result': return 60;
      case 'elevation': return 72;
      case 'stadium_name': return 140;
      case 'city': return 90;
      case 'state': return 60;
      case 'indoor_outdoor': return 80;
      case 'surface_type': return 80;
      case 'temp': return 68;
      case 'humidity': return 68;
      case 'wind': return 68;
      case 'targets': return 64;
      case 'rec': return 64;
      case 'yds': return 72;
      case 'td': return 56;
      case 'smart_projection': return 110;
      case 'predicted_alpha': return 90;
      default: return 80;
    }
  };

  const gridTemplateColumns = useMemo(
    () => columns.map(col => {
      const min = getColMin(col);
      if (col === 'player_name') return `minmax(${min}px, 2fr)`;
      if (col === 'stadium_name') return `minmax(${min}px, 1.5fr)`;
      return `minmax(${min}px, 1fr)`;
    }).join(' '),
    [columns]
  );

  const stickyOffsets = useMemo(() => {
    const offsets = new Map<SortField, number>();
    let runningLeft = 0;
    for (const col of columns) {
      if (STICKY_COLUMNS.has(col)) {
        offsets.set(col, runningLeft);
        runningLeft += getColMin(col);
      } else if (runningLeft > 0) break;
    }
    return offsets;
  }, [columns]);

  const getStickyStyle = (col: SortField): React.CSSProperties => {
    if (!STICKY_COLUMNS.has(col)) return {};
    return {
      position: 'sticky',
      left: stickyOffsets.get(col) ?? 0,
      zIndex: 10,
    };
  };

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 15,
  });

  // ── Cell Formatting ───────────────────────────────────────────
  const formatCell = (col: SortField, value: unknown, index: number): React.ReactNode => {
    // Rank badge
    if (col === 'rank') {
      const rank = index + 1;
      const badgeColor = rank === 1
        ? 'bg-amber-500/15 border-amber-500/30 text-amber-400'
        : rank === 2
          ? 'bg-slate-400/10 border-slate-400/20 text-slate-300'
          : rank === 3
            ? 'bg-orange-500/10 border-orange-500/20 text-orange-400'
            : 'bg-slate-800/60 border-white/5 text-slate-400';
      return (
        <span className={cn("w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold border", badgeColor)}>
          {rank}
        </span>
      );
    }

    // Player name — standalone branch, no fallthrough
    if (col === 'player_name') {
      return <span className="font-semibold text-slate-100 text-sm truncate">{value as string}</span>;
    }

    // Team badge
    if (col === 'team') {
      return (
        <span className="px-2 py-0.5 rounded bg-slate-950/60 border border-white/[0.04] text-[10px] font-black uppercase tracking-tight text-slate-400">
          {(value as string) || 'FA'}
        </span>
      );
    }

    // Game result with W/L coloring
    if (col === 'game_result') {
      const result = value as string;
      if (!result || result === '-') return <span className="text-slate-600">—</span>;
      const isWin = result.startsWith('W');
      return (
        <span className={cn("text-xs font-bold", isWin ? "text-emerald-400" : "text-red-400")}>
          {result}
        </span>
      );
    }

    // PPR highlight
    if (col === 'fpts_ppr' || col === 'fpts_ppr_per_game' || col === 'smart_projection') {
      return (
        <span className={cn(
          "font-bold text-sm",
          col === 'smart_projection' ? "text-purple-400" : "text-blue-400"
        )}>
          {typeof value === 'number' ? value.toFixed(1) : (String(value ?? '—'))}
        </span>
      );
    }

    // Alpha Delta with Arrows
    if (col === 'predicted_alpha') {
      const alpha = typeof value === 'number' ? value : 0;
      const isPos = alpha >= 0;
      return (
        <div className="flex items-center gap-1.5">
          <span className={cn("font-bold text-sm", isPos ? "text-emerald-400" : "text-rose-400")}>
            {isPos ? '+' : ''}{alpha.toFixed(1)}
          </span>
          {alpha !== 0 && (
            <motion.div initial={{ scale: 0.5 }} animate={{ scale: 1 }}>
              {isPos 
                ? <ChevronUp size={14} className="text-emerald-400" />
                : <ChevronDown size={14} className="text-rose-400" />
              }
            </motion.div>
          )}
        </div>
      );
    }

    // Numbers
    if (typeof value === 'number') {
      if (INTEGER_COLUMNS.has(col) || Number.isInteger(value)) {
        return <span className="text-sm tabular-nums">{Math.round(value)}</span>;
      }
      return <span className="text-sm tabular-nums">{value.toFixed(1)}</span>;
    }

    // Strings / nulls
    return <span className="text-sm text-slate-400">{value !== null && value !== undefined ? String(value) : '—'}</span>;
  };

  // ── Loading State ─────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="bg-slate-900/30 backdrop-blur-xl border border-slate-800/40 rounded-2xl overflow-hidden p-6">
        <div className="space-y-3">
          <Skeleton className="h-10 w-full rounded-lg" />
          <Skeleton className="h-14 w-full rounded-xl" count={10} />
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-slate-900/30 border border-slate-800/40 rounded-2xl p-16 text-center">
        <p className="text-slate-500 text-sm">{en.states.empty}</p>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="bg-slate-900/30 backdrop-blur-xl border border-slate-800/40 rounded-2xl shadow-2xl relative overflow-auto scroll-smooth custom-scrollbar h-[750px]"
    >
      <div className="min-w-max">
        {/* ── Column Group Header ────────────────────────────────── */}
        <div className="sticky top-0 z-40 border-b border-white/[0.03]">
          <div className="flex bg-slate-950/80 backdrop-blur-md">
            {columnGroups.map((group) => {
              const groupWidth = group.columns.length;
              return (
                <div
                  key={group.label}
                  className="flex items-center justify-center border-r border-white/[0.03] last:border-r-0"
                  style={{
                    flex: groupWidth,
                    minWidth: group.columns.reduce((sum, c) => sum + getColMin(c), 0),
                  }}
                >
                  <span className={cn("text-[10px] font-semibold uppercase tracking-[0.15em] py-2", group.accent)}>
                    {group.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Column Headers ─────────────────────────────────────── */}
        <div
          className="sticky top-[33px] z-30 bg-slate-900/95 backdrop-blur-md border-b border-white/[0.04]"
          style={{ display: 'grid', gridTemplateColumns }}
        >
          {columns.map((key) => (
            <div
              key={key}
              onClick={() => onSort(key)}
              style={getStickyStyle(key)}
              className={cn(
                "px-3 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-500 cursor-pointer hover:text-slate-200 transition-colors flex items-center justify-center gap-1.5 select-none",
                STICKY_COLUMNS.has(key) && "bg-slate-900/98 shadow-[2px_0_8px_-2px_rgba(0,0,0,0.4)]",
                sortBy === key && "text-blue-400"
              )}
            >
              {t[key] || key}
              {sortBy === key && (
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ duration: 0.15 }}>
                  {sortOrder === 'asc'
                    ? <ChevronUp size={12} className="text-blue-400" />
                    : <ChevronDown size={12} className="text-blue-400" />
                  }
                </motion.div>
              )}
            </div>
          ))}
        </div>

        {/* ── Table Body ─────────────────────────────────────────── */}
        <div
          className="relative w-full"
          style={{ height: `${virtualizer.getTotalSize()}px` }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = data[virtualRow.index];
            const isEven = virtualRow.index % 2 === 0;

            return (
              <div
                key={row.player_id + ('week' in row ? String(row.week) : '')}
                onClick={() => onRowClick(row)}
                style={{
                  display: 'grid',
                  gridTemplateColumns,
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                className={cn(
                  "group cursor-pointer border-b border-white/[0.03] transition-colors duration-150",
                  isEven ? "bg-transparent" : "bg-white/[0.01]",
                  "hover:bg-blue-500/[0.04]"
                )}
              >
                {columns.map((col) => {
                  const value = (row as any)[col];
                  const isSticky = STICKY_COLUMNS.has(col);
                  const sticky = getStickyStyle(col);

                  return (
                    <div
                      key={col}
                      style={sticky}
                      className={cn(
                        "px-3 flex items-center justify-center transition-colors",
                        isSticky && "bg-slate-950/90 group-hover:bg-slate-900/95 shadow-[2px_0_8px_-2px_rgba(0,0,0,0.3)]",
                        !isSticky && isEven ? "" : !isSticky ? "bg-white/[0.01]" : "",
                      )}
                    >
                      {formatCell(col, value, virtualRow.index)}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
