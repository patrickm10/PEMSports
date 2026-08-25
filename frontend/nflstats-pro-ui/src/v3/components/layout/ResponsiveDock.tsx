import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Sidebar } from '../navigation/Sidebar';
import { useMediaQuery } from '../../../hooks/useMediaQuery';

export type WorkspaceView = 'dashboard' | 'rankings' | 'player';

interface ResponsiveDockProps {
  children: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
  workspaceView: WorkspaceView;
  onWorkspaceViewChange: (v: WorkspaceView) => void;
  hasSelectedPlayer: boolean;
  onOpenSearch: () => void;
}

export const ResponsiveDock = ({
  children,
  activePosition,
  onPositionChange,
  workspaceView,
  onWorkspaceViewChange,
  hasSelectedPlayer,
  onOpenSearch,
}: ResponsiveDockProps) => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Overlay only renders when isMobile; no effect needed to clear open state on desktop.
  const showMobileNav = isMobile && mobileNavOpen;

  const closeMobileNav = () => setMobileNavOpen(false);

  const handlePositionChange = (pos: string) => {
    closeMobileNav();
    onPositionChange(pos);
  };

  const handleWorkspaceViewChange = (v: WorkspaceView) => {
    closeMobileNav();
    onWorkspaceViewChange(v);
  };

  const lockRankingsFill = workspaceView === 'rankings' && !isMobile;
  const headerSubtitle =
    workspaceView === 'dashboard'
      ? 'Season charts'
      : workspaceView === 'player'
        ? 'Player splits'
        : 'Fantasy leaderboard';

  const sidebar = (
    <Sidebar
      activePosition={activePosition}
      onPositionChange={handlePositionChange}
      collapsed={!isMobile && isSidebarCollapsed}
      onToggle={() => {
        if (isMobile) {
          closeMobileNav();
        } else {
          setIsSidebarCollapsed(!isSidebarCollapsed);
        }
      }}
      workspaceView={workspaceView}
      onWorkspaceViewChange={handleWorkspaceViewChange}
      hasSelectedPlayer={hasSelectedPlayer}
      onOpenSearch={() => {
        closeMobileNav();
        onOpenSearch();
      }}
    />
  );

  return (
    <div className="app-mesh-root flex h-screen w-full text-slate-200 overflow-hidden font-sans antialiased">
      {!isMobile && sidebar}

      {showMobileNav && (
        <div className="fixed inset-0 z-40 flex">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close navigation"
            onClick={closeMobileNav}
          />
          <div className="relative z-10 h-full w-[min(220px,85vw)] shadow-2xl">
            {sidebar}
          </div>
        </div>
      )}

      <main className="relative z-[1] flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <header className="h-14 shrink-0 border-b border-white/[0.06] flex items-center justify-between px-4 lg:px-8 glass-card rounded-none border-x-0 border-t-0">
          <div className="flex items-center gap-3 min-w-0">
            {isMobile && (
              <button
                type="button"
                onClick={() => setMobileNavOpen((open) => !open)}
                className="p-2 rounded-lg border border-white/10 text-slate-300 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-sky-500/50"
                aria-label={showMobileNav ? 'Close navigation' : 'Open navigation'}
                aria-expanded={showMobileNav}
              >
                {showMobileNav ? <X size={18} /> : <Menu size={18} />}
              </button>
            )}
            <span className="text-[10px] font-bold tracking-[0.25em] uppercase text-slate-500 truncate">
              PEM Sports
            </span>
            <span className="text-slate-600 hidden sm:inline">·</span>
            <span className="text-xs font-semibold text-slate-300 hidden sm:inline truncate">
              {headerSubtitle}
            </span>
          </div>
        </header>

        <section
          className={
            lockRankingsFill
              ? 'flex-1 min-h-0 overflow-hidden px-3 py-4 lg:px-6 lg:py-5'
              : 'flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-3 py-4 lg:px-6 lg:py-5 custom-scrollbar'
          }
        >
          {children}
        </section>
      </main>
    </div>
  );
};
