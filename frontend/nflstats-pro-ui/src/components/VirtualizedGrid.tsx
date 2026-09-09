import React, { useMemo, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import type { CellContext, ColumnDef, SortingState } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import { PUBLIC_DEFAULT_PLAYER_IMG, staticAssetUrl } from '../utils/backendOrigin';
import { useMediaQuery } from '../hooks/useMediaQuery';
import type { Ranking } from '../models/Ranking';
import type { ResolvedMetric } from '../utils/metrics';
import { formatMetricValue } from '../utils/metrics';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function resolveHeadshotSrc(headshot: string | null): string {
  if (!headshot) return PUBLIC_DEFAULT_PLAYER_IMG;
  return staticAssetUrl(headshot);
}

export type GridDensity = 'compact' | 'standard' | 'expert';

type GridRow = Record<string, unknown>;

interface GridColumnMeta {
  kind: ColumnKind;
  align: 'left' | 'right' | 'center';
  optional: boolean;
}

interface VirtualizedGridProps {
  data: GridRow[];
  onRowClick?: (row: GridRow) => void;
  viewMode?: 'season' | 'weekly';
  density?: GridDensity;
  emptyMessage?: string;
  resolvedMetric?: ResolvedMetric | null;
}

// ── Column classification ────────────────────────────────────────────────────
//
// Instead of a chained ternary on key names, every column is tagged with a
// kind. Width, alignment, and optionality derive from the kind. New bake_db
// columns pick up reasonable defaults automatically.
type ColumnKind = 'rank' | 'name' | 'badge' | 'int' | 'decimal' | 'pct' | 'context' | 'result';

const HIDDEN_KEYS = new Set<string>([
  'player_id',
  'player',
  'position',
  'headshot_url',
  'fpts_ppr',
  'fpts_ppr_per_game',
]);

const HIDDEN_WEEKLY = new Set<string>([
  'games_played',
  'fpts_per_game',
  'season',
]);

// Columns that collapse under tight viewports via @container queries.
// The CSS hides `[data-optional="true"]` below 1200px.
const OPTIONAL_UNDER_1200: ReadonlySet<string> = new Set([
  'sacks',
  'fumbles',
  'temp',
  'humidity',
  'wind',
]);

// Columns only shown in 'expert' density. In 'standard' these collapse into
// a hoverable context cell or are hidden outright.
const EXPERT_ONLY: ReadonlySet<string> = new Set([
  'temp',
  'humidity',
  'wind',
]);

const STADIUM_METADATA_KEYS: readonly string[] = [
  'stadium_name',
  'city',
  'state',
  'indoor_outdoor',
  'surface_type',
  'elevation',
  'weather_impact',
  'year_opened',
];

// Short headers for dense numeric columns. Full name kept in the `title`
// attribute so screen readers + tooltips still get the canonical label.
const HEADER_ABBR: Record<string, string> = {
  rank: '#',
  player_name: 'Player',
  team: 'Team',
  year: 'Season',
  week: 'Week',
  opponent: 'Opp',
  games_played: 'G',
  fpts: 'Fantasy points',
  fpts_ppr: 'PPR',
  fpts_per_game: 'Per game',
  fpts_ppr_per_game: 'PPR/G',
  yds: 'Yards',
  td: 'TD',
  att: 'Att',
  cmp: 'Comp',
  int: 'Int',
  sacks: 'Sacks',
  fumbles: 'Fum',
  tgt: 'Tgt',
  rec: 'Rec',
  rush_yds: 'Rush yds',
  rush_td: 'Rush TD',
  rush_att: 'Rush att',
  r_yds: 'Rush yds',
  r_td: 'Rush TD',
  r_att: 'Rush att',
  stadium_name: 'Stadium',
  city: 'City',
  state: 'State',
  surface_type: 'Surface',
  indoor_outdoor: 'Venue',
  elevation: 'Elev',
  weather_impact: 'Weather',
  year_opened: 'Opened',
  temp: 'Temp',
  humidity: 'Hum',
  wind: 'Wind',
  game_result: 'W/L',
  rost: 'Rostered',
  pct: 'Comp %',
  fl: 'Fum',
};

const HEADER_TITLE: Record<string, string> = {
  rank: 'Rank',
  player_name: 'Player name',
  team: 'Team',
  year: 'Season year',
  week: 'Week',
  opponent: 'Opponent',
  games_played: 'Games played',
  fpts: 'Fantasy points',
  fpts_ppr: 'PPR fantasy points',
  fpts_per_game: 'Fantasy points per game',
  fpts_ppr_per_game: 'PPR fantasy points per game',
  yds: 'Yards',
  td: 'Touchdowns',
  att: 'Attempts',
  cmp: 'Completions',
  int: 'Interceptions',
  sacks: 'Sacks',
  fumbles: 'Fumbles',
  tgt: 'Targets',
  rec: 'Receptions',
  rush_yds: 'Rushing yards',
  rush_td: 'Rushing touchdowns',
  rush_att: 'Rushing attempts',
  r_yds: 'Rushing yards',
  r_td: 'Rushing touchdowns',
  r_att: 'Rushing attempts',
  stadium_name: 'Stadium',
  surface_type: 'Playing surface',
  indoor_outdoor: 'Indoor or outdoor',
  weather_impact: 'Weather impact',
  game_result: 'Game result',
  rost: 'Roster percentage',
  pct: 'Completion percentage',
  fl: 'Fumbles',
};

function titleCaseKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

const COUNTING_STAT_KEYS = new Set<string>([
  'td',
  'cmp',
  'att',
  'int',
  'tgt',
  'rec',
  'yds',
  'targets',
  'sacks',
  'fumbles',
  'rush_yds',
  'rush_td',
  'fgm',
  'fga',
  'xpm',
  'xpa',
  'lg',
  'yds_allowed',
  'td_allowed',
  'fum_rec',
  'fum_for',
  'def_td',
  'safety',
  'st_td',
]);

function classify(key: string): ColumnKind {
  if (key === 'rank') return 'rank';
  if (key === 'player_name' || key === 'name') return 'name';
  if (key === 'team' || key === 'opponent') return 'badge';
  if (key === 'game_result') return 'result';
  if (
    key === 'year' ||
    key === 'week' ||
    key === 'games_played' ||
    key === 'year_opened' ||
    COUNTING_STAT_KEYS.has(key) ||
    key.endsWith('_yds') ||
    key.endsWith('_td')
  ) {
    return 'int';
  }
  if (
    key === 'stadium_name' ||
    key === 'city' ||
    key === 'state' ||
    key === 'indoor_outdoor' ||
    key === 'surface_type' ||
    key === 'weather_impact'
  ) {
    return 'context';
  }
  if (key === 'rost' || key === 'pct' || key.endsWith('_pct')) return 'pct';
  return 'decimal';
}

const WIDTH_BY_KIND: Record<ColumnKind, number> = {
  rank: 52,
  name: 236,
  badge: 68,
  int: 60,
  decimal: 72,
  pct: 72,
  context: 140,
  result: 88,
};

const WIDTH_BY_KEY: Record<string, number> = {
  fpts: 150,
  stadium_name: 220,
  city: 140,
  state: 64,
  indoor_outdoor: 112,
  surface_type: 104,
  elevation: 92,
  weather_impact: 128,
  year_opened: 104,
};

const ALIGN_BY_KIND: Record<ColumnKind, 'left' | 'right' | 'center'> = {
  rank: 'center',
  name: 'left',
  badge: 'center',
  int: 'right',
  decimal: 'right',
  pct: 'right',
  context: 'center',
  result: 'center',
};

// ── Density presets ──────────────────────────────────────────────────────────
const DENSITY: Record<
  GridDensity,
  { rowHeight: number; padY: string; padX: string; fontSize: string; headerPadY: string }
> = {
  compact: { rowHeight: 32, padY: '5px', padX: '7px', fontSize: '12px', headerPadY: '7px' },
  standard: { rowHeight: 40, padY: '7px', padX: '9px', fontSize: '13.5px', headerPadY: '9px' },
  expert: { rowHeight: 46, padY: '9px', padX: '11px', fontSize: '15px', headerPadY: '11px' },
};

const HEADLINE_STAT_KEYS = new Set([
  'fpts_ppr',
  'fpts',
  'fpts_per_game',
  'fpts_ppr_per_game',
  'yds',
  'td',
  'rush_yds',
  'rush_td',
  'rec',
  'tgt',
]);

const MOBILE_CARD_H: Record<GridDensity, number> = {
  compact: 104,
  standard: 118,
  expert: 132,
};

function rankTier(rank: unknown, total: number): 'elite' | 'solid' | undefined {
  const r = typeof rank === 'number' ? rank : Number(rank);
  if (!Number.isFinite(r) || total <= 0) return undefined;
  const top25 = Math.max(1, Math.ceil(total * 0.25));
  const top60 = Math.max(1, Math.ceil(total * 0.6));
  if (r <= top25) return 'elite';
  if (r <= top60) return 'solid';
  return undefined;
}

type DisplayItem =
  | { kind: 'band'; key: string; tier: 'elite' | 'solid'; label: string; note: string }
  | { kind: 'player'; key: string; tableIndex: number };

const BAND_H = 32;
const MOBILE_BAND_H = 28;

function buildDisplayItems(
  rows: Array<{ id: string; original: GridRow }>,
  sortId: string | undefined,
  sortDesc: boolean,
): DisplayItem[] {
  const grouped = sortId === 'rank' && !sortDesc;
  const items: DisplayItem[] = [];
  let seenElite = false;
  let seenSolid = false;
  const total = rows.length;
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (grouped) {
      const tier = rankTier(row.original.rank, total);
      if (tier === 'elite' && !seenElite) {
        items.push({
          kind: 'band',
          key: 'band-elite',
          tier: 'elite',
          label: 'Tier 1',
          note: 'top 25%',
        });
        seenElite = true;
      } else if (tier === 'solid' && !seenSolid) {
        items.push({
          kind: 'band',
          key: 'band-solid',
          tier: 'solid',
          label: 'Tier 2',
          note: 'next through 60%',
        });
        seenSolid = true;
      }
    }
    items.push({ kind: 'player', key: row.id, tableIndex: i });
  }
  return items;
}

function TierBandLabel({
  tier,
  label,
  note,
}: {
  tier: 'elite' | 'solid';
  label: string;
  note: string;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          tier === 'elite' ? 'bg-emerald-500' : 'bg-amber-500',
        )}
        aria-hidden
      />
      <span className="text-[11px] font-semibold text-slate-300">{label}</span>
      <span className="text-[11px] font-normal text-slate-500">{note}</span>
    </span>
  );
}

function PlayerAvatar({
  row,
  imgClassName,
}: {
  row: Record<string, unknown>;
  imgClassName: string;
}) {
  const headshot = typeof row.headshot_url === 'string' ? row.headshot_url : null;
  const apiDefault = staticAssetUrl('/headshots/default-player.jpg');
  const src = resolveHeadshotSrc(headshot);
  return (
    <img
      src={src}
      alt=""
      className={imgClassName}
      onError={(e) => {
        const el = e.currentTarget;
        const step = el.dataset.fb ?? '0';
        if (step === '0') {
          el.dataset.fb = '1';
          el.src = apiDefault;
          return;
        }
        if (step === '1') {
          el.dataset.fb = '2';
          el.src = PUBLIC_DEFAULT_PLAYER_IMG;
          return;
        }
        el.onerror = null;
      }}
    />
  );
}

function MobilePlayerCard({
  row,
  tier,
  density,
  metric,
  tabIndex,
  onClick,
  onKeyDown,
}: {
  row: Record<string, unknown>;
  tier?: 'elite' | 'solid';
  density: GridDensity;
  metric: ResolvedMetric | null;
  tabIndex: number;
  onClick: () => void;
  onKeyDown: (event: React.KeyboardEvent) => void;
}) {
  const name = String(row.player_name ?? row.name ?? '—');
  const team = row.team != null ? String(row.team) : '—';
  const rank = row.rank;
  const fmt = (v: unknown, digits = 2) =>
    typeof v === 'number' && Number.isFinite(v)
      ? v.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
      : '—';
  const pad = density === 'compact' ? 'p-3' : density === 'expert' ? 'p-4' : 'p-3.5';
  const imgSize = density === 'compact' ? 'h-10 w-10' : density === 'expert' ? 'h-14 w-14' : 'h-12 w-12';
  const primaryValue = metric ? metric.getValue(row as Ranking) : null;

  return (
    <button
      type="button"
      data-row-activator="true"
      tabIndex={tabIndex}
      aria-label={`Open analytics for ${name}`}
      onClick={onClick}
      onKeyDown={onKeyDown}
      data-tier={tier}
      className={cn(
        'w-full text-left player-card-shell group/row',
        pad,
        'flex flex-col gap-3',
      )}
    >
      <div className="flex items-start gap-3">
        <PlayerAvatar
          row={row}
          imgClassName={cn(
            imgSize,
            'rounded-full object-cover shrink-0 ring-1 ring-white/10 bg-slate-800 transition-transform duration-200 group-hover/row:scale-105',
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-500 tabular-nums">
              #{rank != null && rank !== '' ? String(rank) : '—'}
            </span>
            <span className="truncate font-bold text-white">{name}</span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{team}</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 pt-1 border-t border-white/[0.06]">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
            {metric?.shortLabel ?? 'Stat'}
          </p>
          <p className="text-sm font-bold text-white tabular-nums">
            {metric ? formatMetricValue(primaryValue) : '—'}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Yards</p>
          <p className="text-sm font-bold text-white tabular-nums">{fmt(row.yds, 0)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">TD</p>
          <p className="text-sm font-bold text-white tabular-nums">{fmt(row.td, 0)}</p>
        </div>
      </div>
    </button>
  );
}

export const VirtualizedGrid: React.FC<VirtualizedGridProps> = ({
  data,
  onRowClick,
  viewMode = 'season',
  density = 'standard',
  emptyMessage = 'No player data for this view.',
  resolvedMetric = null,
}) => {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'rank', desc: false },
  ]);
  const [activeRowIndex, setActiveRowIndex] = React.useState(0);
  const parentRef = useRef<HTMLDivElement>(null);

  const maxFpts = useMemo(() => {
    let max = 0;
    for (const row of data) {
      const v = row.fpts;
      if (typeof v === 'number' && Number.isFinite(v) && v > max) max = v;
    }
    return max;
  }, [data]);

  const columns = useMemo<ColumnDef<GridRow>[]>(() => {
    if (!data.length) return [];

    const keys = Object.keys(data[0]);

    let filteredKeys = keys.filter((k) => !HIDDEN_KEYS.has(k));
    if (viewMode === 'weekly') {
      filteredKeys = filteredKeys.filter((k) => !HIDDEN_WEEKLY.has(k));
    }
    if (density !== 'expert') {
      filteredKeys = filteredKeys.filter((k) => !EXPERT_ONLY.has(k));
    }

    // Column order: rank, player_name, opp, headline KPIs, position-specific
    // stats in bake_db order, context, then Team / YR / G (and week when weekly).
    const leadKeys: string[] = [];
    for (const k of ['rank', 'player_name', 'opponent']) {
      if (filteredKeys.includes(k)) leadKeys.push(k);
    }

    const trailKeys: string[] = [];
    for (const k of ['team', 'year', 'games_played', 'week']) {
      if (filteredKeys.includes(k)) trailKeys.push(k);
    }

    const middle = filteredKeys.filter(
      (k) => !leadKeys.includes(k) && !trailKeys.includes(k),
    );

    // Inside "middle", float `fpts` to the front so the primary metric is
    // immediately adjacent to identity columns.
    const fptsIdx = middle.indexOf('fpts');
    if (fptsIdx > 0) {
      middle.splice(fptsIdx, 1);
      middle.unshift('fpts');
    }

    // Stadium metadata is displayed as a complete ordered group.
    const stadiumKeys = STADIUM_METADATA_KEYS.filter((k) => middle.includes(k));
    const contextKeys = middle.filter(
      (k) => classify(k) === 'context' && !stadiumKeys.includes(k),
    );
    const coreMiddle = middle.filter(
      (k) => !contextKeys.includes(k) && !stadiumKeys.includes(k),
    );
    const finalKeys = [...leadKeys, ...coreMiddle, ...stadiumKeys, ...contextKeys, ...trailKeys];

    return finalKeys.map((key) => {
      const kind = classify(key);
      return {
        id: key,
        accessorKey: key,
        header: () => {
          const label = HEADER_ABBR[key] ?? titleCaseKey(key);
          const title = HEADER_TITLE[key] ?? titleCaseKey(key);
          return (
            <span title={title} className="whitespace-nowrap">
              {label}
            </span>
          );
        },
        cell: (info: CellContext<GridRow, unknown>) => {
          const val = info.getValue();

          if (key === 'player_name' || key === 'name') {
            const row = info.row.original;
            const label =
              val === null || val === undefined || val === ''
                ? '—'
                : String(val);
            return (
              <div className="flex items-center gap-2 min-w-0">
                <PlayerAvatar
                  row={row}
                  imgClassName="h-6 w-6 rounded-full object-cover shrink-0 ring-1 ring-white/10 bg-slate-800 transition-transform duration-200 ease-out group-hover/row:scale-110 group-hover/row:ring-sky-400/40"
                />
                <span className="truncate font-bold tracking-tight text-white">
                  {label}
                </span>
              </div>
            );
          }

          if (key === 'fpts') {
            if (val === null || val === undefined || val === '') {
              return (
                <div className="flex min-w-0 items-center gap-2.5">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-white/[0.06]" />
                  <span className="null-value min-w-[2.75rem] text-right">—</span>
                </div>
              );
            }
            if (typeof val === 'number' && Number.isFinite(val)) {
              const width =
                maxFpts > 0 ? Math.max(0, Math.min(100, (val / maxFpts) * 100)) : 0;
              const formatted = val.toLocaleString(undefined, {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
              });
              return (
                <div className="flex min-w-0 items-center gap-2.5">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-sm bg-white/[0.06]">
                    <div
                      className="h-1.5 rounded-sm bg-sky-400"
                      style={{ width: `${width}%` }}
                    />
                  </div>
                  <span className="stat-primary min-w-[2.75rem] text-right tabular-nums">
                    {formatted}
                  </span>
                </div>
              );
            }
          }

          if (val === null || val === undefined || val === '') {
            return <span className="null-value">—</span>;
          }
          if (typeof val === 'number') {
            if (key === 'rank') {
              return <span className="font-bold text-white tabular-nums">{val.toString()}</span>;
            }
            if (key === 'year' || key === 'week' || kind === 'int') {
              return <span className="text-slate-400">{val.toString()}</span>;
            }
            const digits = kind === 'pct' ? 1 : 2;
            const formatted = val.toLocaleString(undefined, {
              minimumFractionDigits: digits,
              maximumFractionDigits: digits,
            });
            if (HEADLINE_STAT_KEYS.has(key)) {
              return <span className="stat-primary">{formatted}</span>;
            }
            return <span className="text-slate-400">{formatted}</span>;
          }
          return String(val);
        },
        size: WIDTH_BY_KEY[key] ?? WIDTH_BY_KIND[kind],
        meta: {
          kind,
          align: key === 'fpts' ? 'left' : ALIGN_BY_KIND[kind],
          optional: OPTIONAL_UNDER_1200.has(key),
        } satisfies GridColumnMeta,
      } satisfies ColumnDef<GridRow>;
    });
  }, [data, viewMode, density, maxFpts]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    columnResizeMode: 'onChange',
  });

  const { rows } = table.getRowModel();
  const preset = DENSITY[density];
  const isMobile = useMediaQuery('(max-width: 768px)');

  const displayItems = useMemo(
    () =>
      buildDisplayItems(
        rows,
        sorting[0]?.id,
        Boolean(sorting[0]?.desc),
      ),
    [rows, sorting],
  );

  const displayIndexByTableIndex = useMemo(() => {
    const map = new Map<number, number>();
    displayItems.forEach((item, index) => {
      if (item.kind === 'player') map.set(item.tableIndex, index);
    });
    return map;
  }, [displayItems]);

  React.useEffect(() => {
    if (rows.length === 0) {
      if (activeRowIndex !== 0) setActiveRowIndex(0);
      return;
    }
    if (activeRowIndex > rows.length - 1) {
      setActiveRowIndex(0);
    }
  }, [rows.length, activeRowIndex]);

  const rowVirtualizer = useVirtualizer({
    count: displayItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      if (displayItems[index]?.kind === 'band') {
        return isMobile ? MOBILE_BAND_H : BAND_H;
      }
      return isMobile ? MOBILE_CARD_H[density] : preset.rowHeight;
    },
    overscan: isMobile ? 8 : 20,
  });

  const focusRow = (index: number) => {
    if (rows.length === 0) return;
    const next = Math.max(0, Math.min(rows.length - 1, index));
    setActiveRowIndex(next);
    rowVirtualizer.scrollToIndex(displayIndexByTableIndex.get(next) ?? next);
    window.requestAnimationFrame(() => {
      const el = parentRef.current?.querySelector<HTMLElement>(
        `[data-row-index="${next}"] [data-row-activator="true"]`,
      );
      el?.focus();
    });
  };

  const handleRovingKey = (event: React.KeyboardEvent, index: number) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusRow(index + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusRow(index - 1);
    }
  };

  // Compute sticky offsets up-front so left-frozen columns stack correctly.
  const visibleLeafColumns = table.getVisibleLeafColumns();
  const rankIdx = visibleLeafColumns.findIndex((c) => c.id === 'rank');
  const rankWidth =
    rankIdx !== -1 ? visibleLeafColumns[rankIdx]!.getSize() : 0;

  const shellStyle: React.CSSProperties = {
    height: '100%',
    width: '100%',
    overflow: 'auto',
    borderRadius: '16px',
    ['--grid-row-h' as string]: `${preset.rowHeight}px`,
    ['--grid-pad-y' as string]: preset.padY,
    ['--grid-pad-x' as string]: preset.padX,
    ['--grid-font-size' as string]: preset.fontSize,
    ['--grid-header-pad-y' as string]: preset.headerPadY,
  };

  if (!data.length) {
    return (
      <div
        className="analysis-grid-shell glass-card flex items-center justify-center min-h-[240px] rounded-2xl px-6"
        data-density={density}
        role="status"
      >
        <p className="text-slate-400 text-sm font-medium text-center max-w-md leading-relaxed">
          {emptyMessage}
        </p>
      </div>
    );
  }

  if (isMobile) {
    const vItems = rowVirtualizer.getVirtualItems();
    const last = vItems.length > 0 ? vItems[vItems.length - 1] : null;
    return (
      <div
        ref={parentRef}
        className="analysis-grid-shell glass-card rounded-2xl"
        data-density={density}
        style={shellStyle}
      >
        <div className="flex flex-col gap-2.5 p-3">
          {vItems.length > 0 && vItems[0].start > 0 && <div style={{ height: vItems[0].start }} />}
          {vItems.map((virtualRow) => {
            const item = displayItems[virtualRow.index];
            if (!item) return null;
            if (item.kind === 'band') {
              return (
                <div
                  key={virtualRow.key}
                  style={{ minHeight: virtualRow.size }}
                  className="flex items-center px-1"
                >
                  <TierBandLabel
                    tier={item.tier}
                    label={item.label}
                    note={item.note}
                  />
                </div>
              );
            }
            const row = rows[item.tableIndex];
            const tier = rankTier(
              (row.original as Record<string, unknown>).rank,
              rows.length,
            );
            return (
              <div
                key={virtualRow.key}
                data-row-index={item.tableIndex}
                style={{ minHeight: virtualRow.size }}
              >
                <MobilePlayerCard
                  row={row.original as Record<string, unknown>}
                  tier={tier}
                  density={density}
                  metric={resolvedMetric}
                  tabIndex={item.tableIndex === activeRowIndex ? 0 : -1}
                  onClick={() => onRowClick?.(row.original)}
                  onKeyDown={(event) => handleRovingKey(event, item.tableIndex)}
                />
              </div>
            );
          })}
          {last && last.end < rowVirtualizer.getTotalSize() && (
            <div style={{ height: rowVirtualizer.getTotalSize() - last.end }} />
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={parentRef}
      className="analysis-grid-shell glass-card min-w-0"
      data-density={density}
      style={shellStyle}
    >
      <div className="min-w-0 h-full">
        <table className="analysis-grid w-max min-w-full">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const colId = header.column.id;
                const meta = (header.column.columnDef.meta ?? {}) as Partial<GridColumnMeta>;
                const align = meta.align ?? 'center';

                const leftOffset =
                  colId === 'rank'
                    ? 0
                    : (colId === 'player_name' || colId === 'name') && rankIdx !== -1
                    ? rankWidth
                    : undefined;

                const sorted = header.column.getIsSorted();
                const ariaSort =
                  sorted === 'asc'
                    ? 'ascending'
                    : sorted === 'desc'
                      ? 'descending'
                      : undefined;

                return (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    scope="col"
                    aria-sort={ariaSort}
                    data-kind={(header.column.columnDef.meta as GridColumnMeta | undefined)?.kind}
                    data-optional={meta.optional || undefined}
                    className={cn(
                      'select-none transition-colors hover:bg-slate-800/80',
                      (colId === 'rank' ||
                        colId === 'player_name' ||
                        colId === 'name') &&
                        'sticky-col',
                      colId === 'rank' &&
                        'border-[#ffffff10] shadow-[4px_0_15px_rgba(0,0,0,0.4)]',
                      (colId === 'player_name' || colId === 'name') && 'sticky-name-col',
                    )}
                    style={{
                      width: header.getSize(),
                      minWidth: header.getSize(),
                      textAlign: align,
                      left: leftOffset,
                    }}
                  >
                    <button
                      type="button"
                      onClick={header.column.getToggleSortingHandler()}
                      className={cn(
                        'flex items-center gap-1.5 w-full bg-transparent border-0 p-0 text-inherit cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/50 rounded-sm',
                        align === 'right' && 'justify-end',
                        align === 'center' && 'justify-center',
                        align === 'left' && 'justify-start',
                      )}
                    >
                      <span className="text-[11px] font-semibold text-slate-400">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </span>
                      {{
                        asc: <span className="text-sky-400 text-[10px]">▲</span>,
                        desc: <span className="text-sky-400 text-[10px]">▼</span>,
                      }[sorted as string] ?? null}
                    </button>
                  </th>
                );
              })}
            </tr>
          ))}
        </thead>

        <tbody className="relative">
          {rowVirtualizer.getVirtualItems().length > 0 &&
            rowVirtualizer.getVirtualItems()[0].start > 0 && (
              <tr>
                <td
                  style={{ height: `${rowVirtualizer.getVirtualItems()[0].start}px` }}
                  colSpan={columns.length}
                />
              </tr>
            )}

          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const item = displayItems[virtualRow.index];
            if (!item) return null;
            if (item.kind === 'band') {
              return (
                <tr
                  key={virtualRow.key}
                  data-band={item.tier}
                  className="pointer-events-none"
                  style={{ height: `${virtualRow.size}px` }}
                >
                  <td
                    colSpan={columns.length}
                    className="tier-band-cell"
                  >
                    <TierBandLabel
                      tier={item.tier}
                      label={item.label}
                      note={item.note}
                    />
                  </td>
                </tr>
              );
            }
            const row = rows[item.tableIndex];
            const tier = rankTier((row.original as Record<string, unknown>).rank, rows.length);
            const playerLabel = String(
              (row.original as Record<string, unknown>).player_name ??
                (row.original as Record<string, unknown>).name ??
                'player',
            );
            return (
              <tr
                key={virtualRow.key}
                data-index={item.tableIndex}
                data-row-index={item.tableIndex}
                data-tier={tier}
                onClick={() => onRowClick?.(row.original)}
                className="group/row cursor-pointer transition-colors"
                style={{ height: `${virtualRow.size}px` }}
              >
                {row.getVisibleCells().map((cell) => {
                  const colId = cell.column.id;
                  const isName = colId === 'player_name' || colId === 'name';
                  const meta = (cell.column.columnDef.meta ?? {}) as Partial<GridColumnMeta>;
                  const align = meta.align ?? 'center';
                  const leftOffset =
                    colId === 'rank'
                      ? 0
                      : isName && rankIdx !== -1
                      ? rankWidth
                      : undefined;

                  return (
                    <td
                      key={cell.id}
                      data-kind={(cell.column.columnDef.meta as GridColumnMeta | undefined)?.kind}
                      data-optional={meta.optional || undefined}
                      className={cn(
                        'transition-all duration-200 group-hover/row:text-white tabular-nums',
                        (colId === 'rank' || isName) && 'sticky-col',
                        colId === 'rank' && 'border-[#ffffff10]',
                        isName && 'sticky-name-col',
                      )}
                      style={{
                        width: cell.column.getSize(),
                        minWidth: cell.column.getSize(),
                        maxWidth: cell.column.getSize(),
                        textAlign: align,
                        left: leftOffset,
                      }}
                    >
                      {isName ? (
                        <button
                          type="button"
                          data-row-activator="true"
                          tabIndex={item.tableIndex === activeRowIndex ? 0 : -1}
                          aria-label={`Open analytics for ${playerLabel}`}
                          className="flex items-center gap-2 min-w-0 w-full text-left bg-transparent border-0 p-0 cursor-pointer"
                          onClick={(event) => {
                            event.stopPropagation();
                            onRowClick?.(row.original);
                          }}
                          onKeyDown={(event) => handleRovingKey(event, item.tableIndex)}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </button>
                      ) : (
                        flexRender(cell.column.columnDef.cell, cell.getContext())
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}

          {rowVirtualizer.getVirtualItems().length > 0 &&
            rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1].end <
              rowVirtualizer.getTotalSize() && (
              <tr>
                <td
                  style={{
                    height: `${
                      rowVirtualizer.getTotalSize() -
                      rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1].end
                    }px`,
                  }}
                  colSpan={columns.length}
                />
              </tr>
            )}
        </tbody>
      </table>
      </div>
    </div>
  );
};
