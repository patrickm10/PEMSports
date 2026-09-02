import React, { useEffect, useRef, useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Sidebar } from '../navigation/Sidebar';
import { useMediaQuery } from '../../../hooks/useMediaQuery';
import { AuthControls } from '../../../components/v2/Auth/AuthControls';
import { positionFullName } from '../../../utils/positionLabels';

export type WorkspaceView = 'dashboard' | 'rankings' | 'player' | 'insights';

interface ResponsiveDockProps {
  children: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
  workspaceView: WorkspaceView;
  onWorkspaceViewChange: (v: WorkspaceView) => void;
  hasSelectedPlayer: boolean;
  onOpenSearch: () => void;
  viewMode: 'season' | 'weekly';
  selectedYear: string;
  selectedWeek: string;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function pageTitle(workspaceView: WorkspaceView, activePosition: string): React.ReactNode {
  if (workspaceView === 'dashboard') return 'Dashboard';
  if (workspaceView === 'player') return 'Player Analytics';
  if (workspaceView === 'insights') return 'Insights';
  return (
    <>
      {positionFullName(activePosition)}{' '}
      <span className="text-sky-400">Rankings</span>
    </>
  );
}

function supportingLabel(
  workspaceView: WorkspaceView,
  viewMode: 'season' | 'weekly',
  selectedYear: string,
  selectedWeek: string,
): string {
  const slice = !selectedYear
    ? viewMode === 'weekly'
      ? 'Weekly games'
      : 'Season totals'
    : viewMode === 'weekly' && selectedWeek
      ? `${selectedYear} · Week ${selectedWeek}`
      : `${selectedYear} season`;

  if (workspaceView === 'dashboard') return `Charts · ${slice}`;
  if (workspaceView === 'player') {
    return 'Trends, opponents, stadium, and surface';
  }
  if (workspaceView === 'insights') {
    return 'How players compare to their own season baseline';
  }
  return slice;
}

export const ResponsiveDock = ({
  children,
  activePosition,
  onPositionChange,
  workspaceView,
  onWorkspaceViewChange,
  hasSelectedPlayer,
  onOpenSearch,
  viewMode,
  selectedYear,
  selectedWeek,
}: ResponsiveDockProps) => {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const showMobileNav = isMobile && mobileNavOpen;

  const closeMobileNav = () => setMobileNavOpen(false);

  useEffect(() => {
    if (!showMobileNav) return;

    const drawer = drawerRef.current;
    const focusables = () =>
      Array.from(drawer?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []).filter(
        (el) => !el.hasAttribute('disabled') && el.tabIndex !== -1,
      );

    const first = focusables()[0];
    first?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        closeMobileNav();
        menuButtonRef.current?.focus();
        return;
      }
      if (e.key !== 'Tab') return;
      const items = focusables();
      if (items.length === 0) return;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstItem) {
        e.preventDefault();
        lastItem.focus();
      } else if (!e.shiftKey && document.activeElement === lastItem) {
        e.preventDefault();
        firstItem.focus();
      }
    };

    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [showMobileNav]);

  const handlePositionChange = (pos: string) => {
    closeMobileNav();
    onPositionChange(pos);
  };

  const handleWorkspaceViewChange = (v: WorkspaceView) => {
    closeMobileNav();
    onWorkspaceViewChange(v);
  };

  const lockRankingsFill = workspaceView === 'rankings' && !isMobile;

  const sidebar = (
    <Sidebar
      activePosition={activePosition}
      onPositionChange={handlePositionChange}
      collapsed={!isMobile && isSidebarCollapsed}
      showCollapseToggle={!isMobile}
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
          <div
            ref={drawerRef}
            id="pem-mobile-nav"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            className="relative z-10 h-full w-[min(220px,85vw)] shadow-2xl"
          >
            {sidebar}
          </div>
        </div>
      )}

      <main
        className="relative z-[1] flex-1 flex flex-col h-full min-w-0 overflow-hidden"
      >
        <header className="min-h-14 shrink-0 border-b border-white/[0.06] bg-slate-950/40">
          <div className="w-full max-w-[1600px] mx-auto grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 px-4 lg:px-6 py-2">
            <div className="flex items-center gap-3 min-w-0">
              {isMobile && (
                <button
                  ref={menuButtonRef}
                  type="button"
                  onClick={() => setMobileNavOpen((open) => !open)}
                  className="p-2 rounded-lg border border-white/10 text-slate-300 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-sky-500/50 shrink-0"
                  aria-label={showMobileNav ? 'Close navigation' : 'Open navigation'}
                  aria-expanded={showMobileNav}
                  aria-controls="pem-mobile-nav"
                  aria-haspopup="dialog"
                >
                  {showMobileNav ? <X size={18} /> : <Menu size={18} />}
                </button>
              )}
              <span className="text-[10px] font-bold tracking-[0.25em] uppercase text-slate-500 shrink-0">
                PEM Sports
              </span>
            </div>
            <div className="flex flex-col items-center justify-center text-center min-w-0 px-2">
              <h1 className="text-sm sm:text-base font-bold tracking-tight text-white leading-tight truncate max-w-[40vw] sm:max-w-none">
                {pageTitle(workspaceView, activePosition)}
              </h1>
              <span className="text-[11px] font-medium text-slate-400 hidden sm:block leading-tight">
                {supportingLabel(workspaceView, viewMode, selectedYear, selectedWeek)}
              </span>
            </div>
            <div className="flex justify-end min-w-0">
              <AuthControls />
            </div>
          </div>
        </header>

        <section
          className={
            lockRankingsFill
              ? 'flex-1 min-h-0 overflow-hidden px-4 py-4 lg:px-6 lg:py-4'
              : 'flex-1 min-h-0 overflow-y-auto overflow-x-hidden px-4 py-4 lg:px-6 lg:py-4 custom-scrollbar'
          }
        >
          {children}
        </section>
      </main>
    </div>
  );
};
