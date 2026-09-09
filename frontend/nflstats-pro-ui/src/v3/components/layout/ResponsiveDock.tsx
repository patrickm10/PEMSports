import React, { useEffect, useRef, useState } from 'react';
import { Menu, X, ChevronRight } from 'lucide-react';
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
  playerCount?: number;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function pageTitle(workspaceView: WorkspaceView, activePosition: string): string {
  if (workspaceView === 'dashboard') return 'Dashboard';
  if (workspaceView === 'player') return 'Player analytics';
  if (workspaceView === 'insights') return 'Insights';
  return `${positionFullName(activePosition)} rankings`;
}

function supportingLabel(
  workspaceView: WorkspaceView,
  viewMode: 'season' | 'weekly',
  selectedYear: string,
  selectedWeek: string,
  playerCount?: number,
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
  if (typeof playerCount === 'number' && playerCount > 0) {
    return `${slice} · ${playerCount} players`;
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
  playerCount,
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
          <div className="w-full max-w-[1600px] mx-auto flex items-end justify-between gap-4 px-4 lg:px-6 py-4">
            <div className="flex items-start gap-3 min-w-0">
              {isMobile && (
                <button
                  ref={menuButtonRef}
                  type="button"
                  onClick={() => setMobileNavOpen((open) => !open)}
                  className="p-1.5 rounded-lg border border-white/10 text-slate-300 hover:text-white hover:bg-white/5 focus-visible:ring-2 focus-visible:ring-sky-500/50 shrink-0 mt-0.5"
                  aria-label={showMobileNav ? 'Close navigation' : 'Open navigation'}
                  aria-expanded={showMobileNav}
                  aria-controls="pem-mobile-nav"
                  aria-haspopup="dialog"
                >
                  {showMobileNav ? <X size={16} /> : <Menu size={16} />}
                </button>
              )}
              <div className="min-w-0">
                {workspaceView === 'rankings' && (
                  <nav
                    aria-label="Breadcrumb"
                    className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-slate-500"
                  >
                    <span>Rankings</span>
                    <ChevronRight size={12} aria-hidden className="shrink-0" />
                    <span className="text-slate-400">
                      {positionFullName(activePosition)}
                    </span>
                  </nav>
                )}
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white leading-tight truncate">
                  {pageTitle(workspaceView, activePosition)}
                </h1>
                <p className="mt-1 text-xs font-normal text-slate-400 leading-tight">
                  {supportingLabel(
                    workspaceView,
                    viewMode,
                    selectedYear,
                    selectedWeek,
                    playerCount,
                  )}
                </p>
              </div>
            </div>
            <div className="flex justify-end shrink-0">
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
