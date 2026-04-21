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

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface VirtualizedGridProps {
  data: any[];
  onRowClick?: (row: any) => void;
  viewMode?: 'season' | 'weekly';
}

export const VirtualizedGrid: React.FC<VirtualizedGridProps> = ({ data, onRowClick, viewMode = 'season' }) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const parentRef = useRef<HTMLDivElement>(null);

  const columns = useMemo<ColumnDef<any>[]>(() => {
    if (!data.length) return [];
    
    const keys = Object.keys(data[0]);
    
    // 1. Filtering Logic
    let filteredKeys = keys.filter(k => ![
      'player_id', 
      'player', // Hide the "Josh Allen (BUF)" version
      'position',
      'fpts_ppr', 
      'fpts_ppr_per_game'
    ].includes(k));

    if (viewMode === 'weekly') {
      filteredKeys = filteredKeys.filter(k => ![
        'games_played', 
        'week', 
        'fpts_per_game',
        'year',
        'season'
      ].includes(k));
    }

    // 2. Base Order: Rank first, then Player Name
    const leadKeys: string[] = [];
    if (filteredKeys.includes('rank')) leadKeys.push('rank');
    if (filteredKeys.includes('player_name')) leadKeys.push('player_name');
    if (filteredKeys.includes('fpts')) leadKeys.push('fpts');
    
    let remainingKeys = filteredKeys.filter(k => !leadKeys.includes(k));

    // 3. Metadata Reordering: Matchup context group, year, team, games_played BEFORE rost
    const matchupGroup = [
      'opponent', 'stadium_name', 'city', 'state', 'indoor_outdoor', 'surface_type', 
      'elevation', 'temp', 'humidity', 'wind', 'game_result'
    ].filter(k => remainingKeys.includes(k));
    
    const metaGroup = ['team', ...matchupGroup, 'year', 'games_played'].filter(k => remainingKeys.includes(k));
    
    const rostIndex = remainingKeys.indexOf('rost');
    
    if (rostIndex !== -1) {
      const preRost = remainingKeys.slice(0, rostIndex).filter(k => !metaGroup.includes(k));
      const postRost = remainingKeys.slice(rostIndex).filter(k => !metaGroup.includes(k));
      remainingKeys = [...preRost, ...metaGroup, ...postRost];
    }

    const finalKeys = [...leadKeys, ...remainingKeys];
    
    return finalKeys.map((key) => ({
      accessorKey: key,
      header: key.replace(/_/g, ' ').toUpperCase(),
      cell: (info: any) => {
        const val = info.getValue();
        if (val === null || val === undefined || val === '') {
          return <span className="null-value">—</span>;
        }
        if (typeof val === 'number') {
          if (key === 'year') {
             return val.toString();
          }
          return val.toLocaleString(undefined, { maximumFractionDigits: (key === 'rank' ? 0 : 2) });
        }
        return val;
      },
      size: key === 'rank' ? 60 : 
            (key === 'stadium_name' ? 120 : 
             (key === 'opponent' ? 170 : 
              (key === 'city' ? 150 : 
               (key === 'team' ? 110 : 115)))),
    }));
  }, [data, viewMode]);

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

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40, 
    overscan: 20,
  });

  return (
    <div
      ref={parentRef}
      className="glass-panel"
      style={{
        height: '100%',
        width: '100%',
        overflow: 'auto',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.05)',
      }}
    >
      <table className="analysis-grid" style={{ width: '100%' }}>
        <thead>
          {table.getHeaderGroups().map((headerGroup: any) => (
            <tr key={headerGroup.id}>

              {headerGroup.headers.map((header: any) => {
                const isSticky = header.id === 'player_name' || header.id === 'name';
                return (
                  <th
                    key={header.id}
                    colSpan={header.colSpan}
                    onClick={header.column.getToggleSortingHandler()}
                    className={cn(
                      'cursor-pointer select-none transition-colors hover:bg-slate-800/80',
                      isSticky ? 'sticky-col border-r border-[#ffffff10] shadow-[4px_0_15px_rgba(0,0,0,0.4)]' : ''
                    )}
                    style={{
                      width: header.getSize(),
                    }}
                  >
                    <div className="flex items-center justify-center gap-2 w-full">
                       <span className="text-[10px] tracking-widest font-black opacity-80 text-center">
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
          {rowVirtualizer.getVirtualItems().length > 0 && rowVirtualizer.getVirtualItems()[0].start > 0 && (
            <tr>
              <td style={{ height: `${rowVirtualizer.getVirtualItems()[0].start}px` }} colSpan={columns.length} />
            </tr>
          )}

          {rowVirtualizer.getVirtualItems().map((virtualRow: any) => {
            const row = rows[virtualRow.index];
            return (
              <tr
                key={virtualRow.key}
                data-index={virtualRow.index}
                onClick={() => onRowClick?.(row.original)}
                className="group/row cursor-pointer transition-colors"
                style={{
                  height: `${virtualRow.size}px`,
                }}
              >
                {row.getVisibleCells().map((cell: any) => {
                  const isSticky = cell.column.id === 'player_name' || cell.column.id === 'name';
                  return (
                    <td
                      key={cell.id}
                      className={cn(
                        'transition-all duration-200 group-hover/row:text-white',
                        isSticky ? 'sticky-col border-r border-[#ffffff10] font-black tracking-tight text-white/90 shadow-[4px_0_15px_rgba(0,0,0,0.3)]' : ''
                      )}
                      style={{
                         width: cell.column.getSize(),
                         minWidth: cell.column.getSize(),
                         maxWidth: cell.column.getSize(),
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            );
          })}

          {rowVirtualizer.getVirtualItems().length > 0 && rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1].end < rowVirtualizer.getTotalSize() && (
             <tr>
               <td style={{ height: `${rowVirtualizer.getTotalSize() - rowVirtualizer.getVirtualItems()[rowVirtualizer.getVirtualItems().length - 1].end}px` }} colSpan={columns.length} />
             </tr>
          )}
        </tbody>

      </table>
    </div>
  );
};
