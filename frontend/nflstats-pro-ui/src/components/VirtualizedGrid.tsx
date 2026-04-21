import React, { useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import type { ColumnDef, SortingState } from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import { PUBLIC_DEFAULT_PLAYER_IMG, staticAssetUrl } from '../utils/backendOrigin';
import { useMediaQuery } from '../hooks/useMediaQuery';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type GridDensity = 'compact' | 'standard' | 'expert';

interface VirtualizedGridProps {
  data: any[];
  onRowClick?: (row: any) => void;
  viewMode?: 'season' | 'weekly';
  density?: GridDensity;
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
  'surface_type',
  'indoor_outdoor',
  'elevation',
  'temp',
  'humidity',
  'wind',
  'city',
  'state',
]);

// Columns only shown in 'expert' density. In 'standard' these collapse into
// a hoverable context cell or are hidden outright.
const EXPERT_ONLY: ReadonlySet<string> = new Set([
  'city',
  'state',
  'indoor_outdoor',
  'elevation',
  'temp',
  'humidity',
  'wind',
  'surface_type',
]);

// Short headers for dense numeric columns. Full name kept in the `title`
// attribute so screen readers + tooltips still get the canonical label.
const HEADER_ABBR: Record<string, string> = {
  rank: '#',
  player_name: 'Player',
  team: 'Team',
  year: 'YR',
  week: 'WK',
  opponent: 'Opp',
  games_played: 'G',
  fpts: 'FP',
  fpts_ppr: 'PPR',
  fpts_per_game: 'FP/G',
  fpts_ppr_per_game: 'PPR/G',
  yds: 'YDS',
  td: 'TD',
  att: 'ATT',
  cmp: 'CMP',
  int: 'INT',
  sacks: 'SK',
  fumbles: 'FUM',
  tgt: 'TGT',
  rec: 'REC',
  rush_yds: 'RYD',
  rush_td: 'RTD',
  stadium_name: 'Stadium',
  surface_type: 'Surf',
  indoor_outdoor: 'Venue',
  elevation: 'Elev',
  temp: 'Temp',
  humidity: 'Hum',
  wind: 'Wind',
  game_result: 'Res',
  rost: 'Rost%',
  pct: 'PCT',
};

function classify(key: string): ColumnKind {
  if (key === 'rank') return 'rank';
  if (key === 'player_name' || key === 'name') return 'name';
  if (key === 'team' || key === 'opponent') return 'badge';
  if (key === 'game_result') return 'result';
  if (key === 'year' || key === 'week' || key === 'games_played') return 'int';
  if (
    key === 'stadium_name' ||
    key === 'city' ||
    key === 'state' ||
    key === 'indoor_outdoor' ||
    key === 'surface_type'
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

function PlayerAvatar({
  row,
  imgClassName,
}: {
  row: Record<string, unknown>;
  imgClassName: string;
}) {
  const pid = row.player_id ?? row.player;
  const apiDefault = staticAssetUrl('/static/players/default-player.png');
  const src = pid
    ? staticAssetUrl(`/static/players/${encodeURIComponent(String(pid))}.png`)
    : PUBLIC_DEFAULT_PLAYER_IMG;
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
  onClick,
}: {
  row: Record<string, unknown>;
  tier?: 'elite' | 'solid';
  density: GridDensity;
  onClick: () => void;
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

  return (
    <motion.button
      type="button"
      layout={false}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      onClick={onClick}
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
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">PPR</p>
          <p className="text-sm font-bold text-white tabular-nums">{fmt(row.fpts_ppr)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">YDS</p>
          <p className="text-sm font-bold text-white tabular-nums">{fmt(row.yds, 0)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">TD</p>
          <p className="text-sm font-bold text-white tabular-nums">{fmt(row.td, 0)}</p>
        </div>
      </div>
    </motion.button>
  );
}

export const VirtualizedGrid: React.FC<VirtualizedGridProps> = ({
  data,
  onRowClick,
  viewMode = 'season',
  density = 'standard',
}) => {
  const [sorting, setSorting] = React.useState<SortingState>([
    { id: 'rank', desc: false },
  ]);
  const parentRef = useRef<HTMLDivElement>(null);

  const columns = useMemo<ColumnDef<any>[]>(() => {
    if (!data.length) return [];

    const keys = Object.keys(data[0]);

    let filteredKeys = keys.filter((k) => !HIDDEN_KEYS.has(k));
    if (viewMode === 'weekly') {
      filteredKeys = filteredKeys.filter((k) => !HIDDEN_WEEKLY.has(k));
    }
    if (density !== 'expert') {
      filteredKeys = filteredKeys.filter((k) => !EXPERT_ONLY.has(k));
    }

    // Column order: rank, player_name, team, year/week, opp, headline KPIs,
    // position-specific stats in bake_db order, context, then fpts_ppr on
    // the right edge (sticky).
    const leadKeys: string[] = [];
    for (const k of ['rank', 'player_name', 'team', 'year', 'week', 'opponent']) {
      if (filteredKeys.includes(k)) leadKeys.push(k);
    }

    const trailKeys: string[] = [];
    if (filteredKeys.includes('fpts_ppr')) trailKeys.push('fpts_ppr');

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

    // Stadium/context keys get pushed toward the end of middle.
    const contextKeys = middle.filter((k) => classify(k) === 'context');
    const coreMiddle = middle.filter((k) => !contextKeys.includes(k));
    const finalKeys = [...leadKeys, ...coreMiddle, ...contextKeys, ...trailKeys];

    return finalKeys.map((key) => {
      const kind = classify(key);
      return {
        id: key,
        accessorKey: key,
        header: () => {
          const label = HEADER_ABBR[key] ?? key.replace(/_/g, ' ').toUpperCase();
          const title = key.replace(/_/g, ' ');
          return (
            <span title={title} className="whitespace-nowrap">
              {label}
            </span>
          );
        },
        cell: (info: any) => {
          const val = info.getValue();

          if (key === 'player_name' || key === 'name') {
            const row = info.row.original as Record<string, unknown>;
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
          return val;
        },
        size: WIDTH_BY_KIND[kind],
        meta: {
          kind,
          align: ALIGN_BY_KIND[kind],
          optional: OPTIONAL_UNDER_1200.has(key),
        } as { kind: ColumnKind; align: 'left' | 'right' | 'center'; optional: boolean },
      } satisfies ColumnDef<any>;
    });
  }, [data, viewMode, density]);

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

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => (isMobile ? MOBILE_CARD_H[density] : preset.rowHeight),
    overscan: isMobile ? 8 : 20,
  });

  // Compute sticky offsets up-front so left-frozen columns stack correctly.
  const visibleLeafColumns = table.getVisibleLeafColumns();
  const rankIdx = visibleLeafColumns.findIndex((c) => c.id === 'rank');
  const rankWidth =
    rankIdx !== -1 ? (visibleLeafColumns[rankIdx] as any).getSize() : 0;

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
        className="analysis-grid-shell glass-card flex items-center justify-center min-h-[240px] rounded-2xl border border-white/10"
        data-density={density}
      >
        <p className="text-slate-400 text-sm font-medium">No player data for this view.</p>
      </div>
    );
  }

  if (isMobile) {
    const vItems = rowVirtualizer.getVirtualItems();
    const last = vItems.length > 0 ? vItems[vItems.length - 1] : null;
    return (
      <div
        ref={parentRef}
        className="analysis-grid-shell glass-card rounded-2xl border border-white/10"
        data-density={density}
        style={shellStyle}
      >
        <div className="flex flex-col gap-2.5 p-3">
          {vItems.length > 0 && vItems[0].start > 0 && <div style={{ height: vItems[0].start }} />}
          {vItems.map((virtualRow) => {
            const row = rows[virtualRow.index];
            const tier = rankTier((row.original as Record<string, unknown>).rank, rows.length);
            return (
              <div key={virtualRow.key} style={{ minHeight: virtualRow.size }}>
                <MobilePlayerCard
                  row={row.original as Record<string, unknown>}
                  tier={tier}
                  density={density}
                  onClick={() => onRowClick?.(row.original)}
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
      <div className="min-w-0 overflow-x-auto h-full">
        <table className="analysis-grid w-max min-w-full">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const colId = header.column.id;
                const isRightSticky = colId === 'fpts_ppr';
                const meta = (header.column.columnDef.meta ?? {}) as {
                  align?: 'left' | 'right' | 'center';
                  optional?: boolean;
                };
                const align = meta.align ?? 'center';

                const leftOffset =
                  colId === 'rank'
                    ? 0
                    : (colId === 'player_name' || colId === 'name') && rankIdx !== -1
                    ? rankWidth
                    : undefined;

                return (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    onClick={header.column.getToggleSortingHandler()}
                    data-kind={(header.column.columnDef.meta as any)?.kind}
                    data-optional={meta.optional || undefined}
                    className={cn(
                      'cursor-pointer select-none transition-colors hover:bg-slate-800/80',
                      (colId === 'rank' ||
                        colId === 'player_name' ||
                        colId === 'name' ||
                        isRightSticky) &&
                        'sticky-col',
                      colId === 'rank' &&
                        'border-[#ffffff10] shadow-[4px_0_15px_rgba(0,0,0,0.4)]',
                      (colId === 'player_name' || colId === 'name') && 'sticky-name-col',
                      isRightSticky &&
                        'sticky-col-right border-[#ffffff10] shadow-[4px_0_15px_rgba(0,0,0,0.4)]',
                    )}
                    style={{
                      width: header.getSize(),
                      minWidth: header.getSize(),
                      textAlign: align,
                      left: leftOffset,
                      right: isRightSticky ? 0 : undefined,
                    }}
                  >
                    <div
                      className={cn(
                        'flex items-center gap-1.5 w-full',
                        align === 'right' && 'justify-end',
                        align === 'center' && 'justify-center',
                        align === 'left' && 'justify-start',
                      )}
                    >
                      <span className="text-[10px] tracking-widest font-bold text-slate-400">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </span>
                      {{
                        asc: <span className="text-sky-400 text-[10px]">▲</span>,
                        desc: <span className="text-sky-400 text-[10px]">▼</span>,
                      }[header.column.getIsSorted() as string] ?? null}
                    </div>
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
            const row = rows[virtualRow.index];
            const tier = rankTier((row.original as Record<string, unknown>).rank, rows.length);
            return (
              <motion.tr
                key={virtualRow.key}
                data-index={virtualRow.index}
                data-tier={tier}
                onClick={() => onRowClick?.(row.original)}
                className="group/row cursor-pointer transition-colors"
                style={{ height: `${virtualRow.size}px` }}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              >
                {row.getVisibleCells().map((cell) => {
                  const colId = cell.column.id;
                  const isRightSticky = colId === 'fpts_ppr';
                  const meta = (cell.column.columnDef.meta ?? {}) as {
                    align?: 'left' | 'right' | 'center';
                    optional?: boolean;
                  };
                  const align = meta.align ?? 'center';
                  const leftOffset =
                    colId === 'rank'
                      ? 0
                      : (colId === 'player_name' || colId === 'name') && rankIdx !== -1
                      ? rankWidth
                      : undefined;

                  return (
                    <td
                      key={cell.id}
                      data-kind={(cell.column.columnDef.meta as any)?.kind}
                      data-optional={meta.optional || undefined}
                      className={cn(
                        'transition-all duration-200 group-hover/row:text-white tabular-nums',
                        (colId === 'rank' ||
                          colId === 'player_name' ||
                          colId === 'name' ||
                          isRightSticky) &&
                          'sticky-col',
                        colId === 'rank' && 'border-[#ffffff10]',
                        (colId === 'player_name' || colId === 'name') &&
                          'sticky-name-col',
                        isRightSticky && 'sticky-col-right border-[#ffffff10]',
                      )}
                      style={{
                        width: cell.column.getSize(),
                        minWidth: cell.column.getSize(),
                        maxWidth: cell.column.getSize(),
                        textAlign: align,
                        left: leftOffset,
                        right: isRightSticky ? 0 : undefined,
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </motion.tr>
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
