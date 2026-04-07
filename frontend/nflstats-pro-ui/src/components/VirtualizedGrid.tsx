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
}

export const VirtualizedGrid: React.FC<VirtualizedGridProps> = ({ data, onRowClick }) => {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const parentRef = useRef<HTMLDivElement>(null);

  const columns = useMemo<ColumnDef<any>[]>(() => {
    if (!data.length) return [];
    
    const keys = Object.keys(data[0]);
    
    return keys.map((key) => ({
      accessorKey: key,
      header: key.replace(/_/g, ' ').toUpperCase(),
      cell: (info: any) => {
        const val = info.getValue();
        if (typeof val === 'number') {
          return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
        }
        return val;
      },
      size: 150, // Default column size
    }));
  }, [data]);

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
                    <div className="flex items-center gap-2">
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

        <tbody
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow: any) => {
            const row = rows[virtualRow.index];
            return (
              <tr
                key={virtualRow.key}
                data-index={virtualRow.index}
                onClick={() => onRowClick?.(row.original)}
                className="group/row cursor-pointer transition-colors"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
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
                      }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>

      </table>
    </div>
  );
};
