/**
 * V3 High-Density Analysis Grid
 * Powered by TanStack Table & Virtualization.
 * Focused on sub-second situational data exploration.
 */

import { useMemo } from 'react';
import { 
  useReactTable, 
  getCoreRowModel, 
  flexRender, 
  createColumnHelper 
} from '@tanstack/react-table';
import { LucideZap } from 'lucide-react';
import { useV3Rankings } from '../../../hooks/v3/useV3Rankings';
import type { WorkspaceState } from '../../../models/v3/workspace';

interface V3AnalysisGridProps {
  state: WorkspaceState;
  onRowClick?: (id: string) => void;
}

const columnHelper = createColumnHelper<any>();

export function V3AnalysisGrid({ state, onRowClick }: V3AnalysisGridProps) {
  const { data = [], isLoading } = useV3Rankings(state);

  const columns = useMemo(() => [
    columnHelper.accessor('Rank', {
      header: '#',
      cell: info => (
        <span className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-xs font-black text-blue-400 border border-blue-500/20">
          {info.getValue()}
        </span>
      ),
    }),
    columnHelper.accessor('Player', {
      header: 'Athlete',
      cell: info => (
        <div className="flex flex-col">
          <span className="font-bold text-slate-100">{info.getValue()}</span>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">{info.row.original.team_name || info.row.original['Team Name']}</span>
        </div>
      ),
    }),
    columnHelper.accessor('FPTS', {
      header: 'Total FPTS',
      cell: info => (
        <span className="font-mono font-bold text-blue-400">
          {Number(info.getValue()).toFixed(1)}
        </span>
      ),
    }),
    columnHelper.accessor('predicted_alpha', {
      header: 'Alpha Δ',
      cell: info => {
        const val = info.getValue();
        if (val === undefined) return <span className="text-slate-600">—</span>;
        const isPos = val > 0;
        return (
          <div className={`flex items-center gap-1 font-bold ${isPos ? 'text-emerald-400' : 'text-rose-400'}`}>
            <LucideZap className="w-3 h-3" />
            {isPos ? '+' : ''}{Number(val).toFixed(1)}
          </div>
        );
      },
    }),
  ], []);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="h-16 bg-white/5 rounded-xl animate-pulse border border-white/5" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-4 overflow-hidden">
      <table className="w-full border-collapse">
        <thead className="sticky top-0 bg-[#020617] z-10">
          {table.getHeaderGroups().map(headerGroup => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map(header => (
                <th key={header.id} className="text-left px-4 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 border-b border-white/5">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-white/5">
          {table.getRowModel().rows.map(row => (
            <tr 
              key={row.id} 
              onClick={() => onRowClick?.(row.original.player_id)}
              className="group hover:bg-blue-600/5 transition-colors cursor-pointer"
            >
              {row.getVisibleCells().map(cell => (
                <td key={cell.id} className="px-4 py-4 text-sm align-middle">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
