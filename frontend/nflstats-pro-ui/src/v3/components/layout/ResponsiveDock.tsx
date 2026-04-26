import React, { useState } from 'react';
import type { GridDensity } from '../../../components/VirtualizedGrid';
import { Sidebar } from '../navigation/Sidebar';

export type WorkspaceView = 'dashboard' | 'rankings' | 'player';

interface ResponsiveDockProps {
  children: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
  workspaceView: WorkspaceView;
  onWorkspaceViewChange: (v: WorkspaceView) => void;
  /** True when the player-analytics surface has a selected player to show. */
  hasSelectedPlayer: boolean;
  /** Open the global search modal (UI store action). */
  onOpenSearch: () => void;
  density: GridDensity;
  setDensity: (d: GridDensity) => void;
}

export const ResponsiveDock = ({
  children,
  activePosition,
  onPositionChange,
  workspaceView,
  onWorkspaceViewChange,
  hasSelectedPlayer,
  onOpenSearch,
  density,
  setDensity,
}: ResponsiveDockProps) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const headerSubtitle =
    workspaceView === 'dashboard'
      ? 'Overview'
      : workspaceView === 'player'
      ? 'Player'
      : 'Leaderboard';

  return (
    <div className="app-mesh-root flex h-screen w-full text-slate-200 overflow-hidden font-sans antialiased">
      <Sidebar
        activePosition={activePosition}
        onPositionChange={onPositionChange}
        collapsed={isSidebarCollapsed}
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        workspaceView={workspaceView}
        onWorkspaceViewChange={onWorkspaceViewChange}
        hasSelectedPlayer={hasSelectedPlayer}
        onOpenSearch={onOpenSearch}
        density={density}
        setDensity={setDensity}
      />

      <main className="relative z-[1] flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <header className="h-14 shrink-0 border-b border-white/[0.06] flex items-center justify-between px-4 lg:px-8 glass-card rounded-none border-x-0 border-t-0">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-[10px] font-bold tracking-[0.25em] uppercase text-slate-500 truncate">
              Midnight Slate
            </span>
            <span className="text-slate-600 hidden sm:inline">·</span>
            <span className="text-xs font-semibold text-slate-300 hidden sm:inline truncate">
              {headerSubtitle}
            </span>
          </div>
        </header>

        <section className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-3 py-5 lg:px-8 lg:py-8 custom-scrollbar">
          {children}
        </section>
      </main>
    </div>
  );
};
