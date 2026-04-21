import React, { useState } from 'react';
import { Sidebar } from '../navigation/Sidebar';

interface ResponsiveDockProps {
  children: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
}

export const ResponsiveDock = ({ 
  children, 
  activePosition, 
  onPositionChange 
}: ResponsiveDockProps) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-full bg-[#020617] text-slate-200 overflow-hidden font-outfit">
      {/* 1. Collapsible Navigation Sidebar (Left) */}
      <Sidebar 
        activePosition={activePosition} 
        onPositionChange={onPositionChange} 
        collapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* 2. Virtualized Analysis Desk (Center - Full Width) */}
      <main className="flex-1 flex flex-col h-full bg-[#020617] overflow-hidden relative">
        <header className="h-16 border-b border-[#1e293b] flex items-center justify-between px-8 bg-[#020617b3] backdrop-blur-xl z-10">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-semibold tracking-[0.2em] uppercase text-slate-500">
              Analysis <span className="text-[#38bdf8]">Workspace</span>
            </h2>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto p-8 relative scrollbar-thin scrollbar-thumb-[#1e293b] scrollbar-track-transparent">
          {children}
        </section>

        {/* Glossy Backdrop Decoration */}
        <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-[#38bdf805] blur-[120px] rounded-full -z-0 pointer-events-none" />
      </main>
    </div>
  );
};
