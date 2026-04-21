import React, { useMemo, useRef } from 'react';
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

import { staticAssetUrl } from '../utils/backendOrigin';

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
  compact: { rowHeight: 30, padY: '4px', padX: '6px', fontSize: '12px', headerPadY: '6px' },
  standard: { rowHeight: 36, padY: '6px', padX: '8px', fontSize: '12.5px', headerPadY: '8px' },
  expert: { rowHeight: 40, padY: '8px', padX: '10px', fontSize: '13px', headerPadY: '10px' },
};

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
            const pid = row.player_id ?? row.player;
            const src = pid
              ? staticAssetUrl(
                  `/static/players/${encodeURIComponent(String(pid))}.png`,
                )
              : staticAssetUrl('/static/players/blank-player.png');
            const label =
              val === null || val === undefined || val === ''
                ? '—'
                : String(val);
            return (
              <div className="flex items-center gap-2 min-w-0">
                <img
                  src={src}
                  alt=""
                  width={24}
                  height={24}
                  className="h-6 w-6 rounded-full object-cover shrink-0 ring-1 ring-white/10 bg-slate-800"
                  onError={(e) => {
                    const el = e.currentTarget;
                    const fb = staticAssetUrl('/static/players/blank-player.png');
                    if (!el.src.includes('blank-player.png')) el.src = fb;
                  }}
                />
                <span className="truncate font-black tracking-tight text-white/90">
                  {label}
                </span>
              </div>
            );
          }

          if (val === null || val === undefined || val === '') {
            return <span className="null-value">—</span>;
          }
          if (typeof val === 'number') {
            if (key === 'year' || key === 'week' || kind === 'int') {
              return val.toString();
            }
            const digits = kind === 'pct' ? 1 : 2;
            return val.toLocaleString(undefined, {
              minimumFractionDigits: digits,
              maximumFractionDigits: digits,
            });
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

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => preset.rowHeight,
    overscan: 20,
  });

  // Compute sticky offsets up-front so left-frozen columns stack correctly.
  const visibleLeafColumns = table.getVisibleLeafColumns();
  const rankIdx = visibleLeafColumns.findIndex((c) => c.id === 'rank');
  const nameIdx = visibleLeafColumns.findIndex(
    (c) => c.id === 'player_name' || c.id === 'name',
  );
  const rankWidth =
    rankIdx !== -1 ? (visibleLeafColumns[rankIdx] as any).getSize() : 0;

  return (
    <div
      ref={parentRef}
      className="analysis-grid-shell glass-panel"
      data-density={density}
      style={{
        height: '100%',
        width: '100%',
        overflow: 'auto',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        ['--grid-row-h' as any]: `${preset.rowHeight}px`,
        ['--grid-pad-y' as any]: preset.padY,
        ['--grid-pad-x' as any]: preset.padX,
        ['--grid-font-size' as any]: preset.fontSize,
        ['--grid-header-pad-y' as any]: preset.headerPadY,
      }}
    >
      <table className="analysis-grid" style={{ width: '100%' }}>
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
                      <span className="text-[10px] tracking-widest font-black opacity-80">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </span>
                      {{
                        asc: <span className="text-primary text-[10px]">▲</span>,
                        desc: <span className="text-primary text-[10px]">▼</span>,
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
            return (
              <tr
                key={virtualRow.key}
                data-index={virtualRow.index}
                onClick={() => onRowClick?.(row.original)}
                className="group/row cursor-pointer transition-colors"
                style={{ height: `${virtualRow.size}px` }}
              >
                {row.getVisibleCells().map((cell) => {
                  const colId = cell.column.id;
                  const isLeftSticky =
                    colId === 'rank' || colId === 'player_name' || colId === 'name';
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
  );
};
