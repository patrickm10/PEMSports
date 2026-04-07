import React from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronUp, ChevronDown, Loader2 } from 'lucide-react';
import { useRankings } from '../../hooks/useRankings';
import { DeltaDrawer } from '../detail/DeltaDrawer';
import type { PlayerStats } from '../../lib/schema';

const columnHelper = createColumnHelper<PlayerStats>();

export function AnalysisDesk() {
  const { pos = 'QB' } = useParams<{ pos: string }>();
  const [searchParams] = useSearchParams();
  const year = searchParams.get('year') || '2025';
  const mode = searchParams.get('mode') || 'seasonal';
  const week = searchParams.get('week') || '1';

  const { data, isLoading, error } = useRankings(pos, year, mode, week);
  
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [selectedPlayer, setSelectedPlayer] = React.useState<any | null>(null);

  const columns = React.useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // Core columns that should always be visible/first
    const baseColKeys = ['player_name', 'team_abbr', 'pos', 'fpts'];
    const otherKeys = Object.keys(data[0]).filter(k => !baseColKeys.includes(k));
    
    return [...baseColKeys, ...otherKeys].map(key => 
      columnHelper.accessor(key as any, {
        header: key.replace(/_/g, ' ').toUpperCase(),
        cell: (info: any) => info.getValue(),
      })
    );
  }, [data]);

  const table = useReactTable({
    data: data || [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const { rows } = table.getRowModel();
  const parentRef = React.useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48, // row height
    overscan: 10,
  });

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center bg-slate-950">
      <Loader2 className="animate-spin text-accent-blue" size={48} />
    </div>
  );

  if (error) return (
    <div className="flex-1 flex items-center justify-center bg-slate-950 text-red-500">
      Error loading analysis data.
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-slate-950 relative">
      <div 
        ref={parentRef} 
        className="flex-1 overflow-auto scrollbar-thin scrollbar-thumb-slate-800"
      >
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-20 bg-slate-900 border-b border-slate-800">
            {table.getHeaderGroups().map((headerGroup: any) => (
              <tr key={headerGroup.id}>

                {headerGroup.headers.map((header: any) => (
                  <th 
                    key={header.id}
                    className="px-4 py-3 text-left text-[10px] font-bold text-slate-500 tracking-widest cursor-pointer hover:text-slate-200 transition-colors uppercase"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-2">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{
                        asc: <ChevronUp size={12} className="text-accent-blue" />,
                        desc: <ChevronDown size={12} className="text-accent-blue" />,
                      }[header.column.getIsSorted() as string] ?? null}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody 
            style={{ 
              height: `${virtualizer.getTotalSize()}px`,
              position: 'relative'
            }}
          >
            {virtualizer.getVirtualItems().map((virtualRow: any) => {
              const row = rows[virtualRow.index];
              return (
                <tr
                  key={row.id}
                  className="absolute left-0 w-full hover:bg-slate-900/50 cursor-pointer group transition-colors border-b border-slate-800/50"
                  style={{ 
                    height: '48px',
                    transform: `translateY(${virtualRow.start}px)` 
                  }}
                  onClick={() => setSelectedPlayer(row.original)}
                >
                  {row.getVisibleCells().map((cell: any) => (
                    <td key={cell.id} className="px-4 py-3 text-sm text-slate-300 group-hover:text-white whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>

        </table>
      </div>

      <DeltaDrawer 
        isOpen={!!selectedPlayer} 
        onClose={() => setSelectedPlayer(null)} 
        playerData={selectedPlayer}
      />
    </div>
  );
}
