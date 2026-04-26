import {
  LayoutDashboard,
  BarChart3,
  Search,
  Settings,
  Shield,
  Crosshair,
  Zap,
  Target,
  Activity,
  Trophy,
  ChevronLeft,
  ChevronRight,
  UserSearch,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useState } from 'react';
import type { GridDensity } from '../../../components/VirtualizedGrid';
import type { WorkspaceView } from '../layout/ResponsiveDock';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface SidebarItemProps {
  icon: LucideIcon;
  label: string;
  active?: boolean;
  onClick?: () => void;
  collapsed?: boolean;
  disabled?: boolean;
  hint?: string;
}

const SidebarItem = ({
  icon: Icon,
  label,
  active,
  onClick,
  collapsed,
  disabled,
  hint,
}: SidebarItemProps) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className={cn(
      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 group text-left',
      active
        ? 'bg-white/10 text-white border border-white/15 shadow-[0_0_0_1px_rgba(56,189,248,0.15)]'
        : 'text-slate-400 hover:text-slate-100 border border-transparent hover:bg-white/[0.04]',
      collapsed && 'justify-center px-0',
      disabled && 'opacity-40 pointer-events-none',
    )}
    title={collapsed ? label : hint}
  >
    <Icon
      size={18}
      className={cn(
        'shrink-0 transition-transform duration-200 group-hover:scale-105',
        active && 'text-sky-400',
      )}
    />
    <AnimatePresence>
      {!collapsed && (
        <motion.span
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          className="text-sm font-medium tracking-wide whitespace-nowrap overflow-hidden"
        >
          {label}
        </motion.span>
      )}
    </AnimatePresence>
  </button>
);

const positions: { id: string; label: string; icon: LucideIcon }[] = [
  { id: 'qb', label: 'Quarterbacks', icon: Crosshair },
  { id: 'rb', label: 'Running Backs', icon: Zap },
  { id: 'wr', label: 'Wide Receivers', icon: Target },
  { id: 'te', label: 'Tight Ends', icon: Activity },
  { id: 'k', label: 'Kickers', icon: Trophy },
  { id: 'dst', label: 'Defense/ST', icon: Shield },
];

interface SidebarProps {
  activePosition: string;
  onPositionChange: (pos: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  workspaceView: WorkspaceView;
  onWorkspaceViewChange: (v: WorkspaceView) => void;
  hasSelectedPlayer: boolean;
  onOpenSearch: () => void;
  density: GridDensity;
  setDensity: (d: GridDensity) => void;
}

export const Sidebar = ({
  activePosition,
  onPositionChange,
  collapsed,
  onToggle,
  workspaceView,
  onWorkspaceViewChange,
  hasSelectedPlayer,
  onOpenSearch,
  density,
  setDensity,
}: SidebarProps) => {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <motion.div
      initial={false}
      animate={{ width: collapsed ? 80 : 220 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      className="h-full border-r border-white/[0.06] py-6 flex flex-col gap-6 z-20 relative overflow-hidden glass-card rounded-none border-y-0 border-l-0"
    >
      <button
        type="button"
        onClick={onToggle}
        className="absolute -right-3 top-12 w-6 h-6 bg-slate-900/90 border border-white/10 rounded-full flex items-center justify-center text-sky-400 hover:bg-sky-500/10 transition-colors z-30 shadow-lg"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      <div className={cn('flex items-center gap-3 px-5 overflow-hidden shrink-0', collapsed && 'px-0 justify-center')}>
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 flex items-center justify-center shadow-[0_0_20px_rgba(56,189,248,0.35)] shrink-0">
          <Shield className="text-white" size={18} />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.h1
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="font-bold text-lg tracking-tight text-white whitespace-nowrap"
            >
              NFLStats <span className="text-sky-400">PRO</span>
            </motion.h1>
          )}
        </AnimatePresence>
      </div>

      <div className="flex flex-col gap-1 flex-1 px-3 overflow-y-auto min-h-0 no-scrollbar">
        {!collapsed && (
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-3 mb-1">Workspace</div>
        )}
        <SidebarItem
          icon={LayoutDashboard}
          label="Dashboard"
          active={workspaceView === 'dashboard'}
          collapsed={collapsed}
          onClick={() => onWorkspaceViewChange('dashboard')}
        />
        <SidebarItem
          icon={BarChart3}
          label="Rankings"
          active={workspaceView === 'rankings'}
          collapsed={collapsed}
          onClick={() => onWorkspaceViewChange('rankings')}
        />
        <SidebarItem
          icon={Search}
          label="Search"
          collapsed={collapsed}
          onClick={onOpenSearch}
          hint="Open search modal"
        />
        <SidebarItem
          icon={UserSearch}
          label="Player"
          active={workspaceView === 'player'}
          collapsed={collapsed}
          onClick={() => onWorkspaceViewChange('player')}
          disabled={!hasSelectedPlayer}
          hint={hasSelectedPlayer ? 'View selected player analytics' : 'Select a player from search to enable'}
        />
        <div className="relative">
          <SidebarItem
            icon={Settings}
            label="Settings"
            active={settingsOpen}
            collapsed={collapsed}
            onClick={() => setSettingsOpen((o) => !o)}
          />
          <AnimatePresence>
            {settingsOpen && !collapsed && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="mt-2 ml-1 p-3 rounded-xl bg-slate-950/60 border border-white/10 backdrop-blur-md"
              >
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Table density</div>
                <div className="flex gap-1 p-0.5 rounded-lg bg-slate-900/80 border border-white/5">
                  {(['compact', 'standard', 'expert'] as const).map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDensity(d)}
                      className={cn(
                        'flex-1 px-2 py-1.5 text-[10px] font-bold uppercase rounded-md transition-colors',
                        density === d
                          ? 'bg-sky-600 text-white shadow shadow-sky-500/20'
                          : 'text-slate-500 hover:text-slate-300',
                      )}
                    >
                      {d.slice(0, 3)}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="h-px bg-white/[0.06] my-2 mx-1" />

        {!collapsed && (
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-3 mb-1">Positions</div>
        )}
        <div className="flex flex-col gap-0.5">
          {positions.map((pos) => (
            <SidebarItem
              key={pos.id}
              icon={pos.icon}
              label={pos.label}
              active={workspaceView === 'rankings' && activePosition === pos.id}
              onClick={() => {
                onWorkspaceViewChange('rankings');
                onPositionChange(pos.id);
              }}
              collapsed={collapsed}
            />
          ))}
        </div>
      </div>

      <div className="px-3 shrink-0">
        <div
          className={cn(
            'flex items-center gap-3 p-3 rounded-xl border border-white/[0.06] bg-white/[0.03] transition-all overflow-hidden',
            collapsed && 'justify-center p-2',
          )}
        >
          <div className="w-8 h-8 rounded-full bg-slate-800 shrink-0 border border-sky-500/20" />
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col min-w-0"
              >
                <span className="text-sm font-semibold text-slate-200 truncate">Analyst</span>
                <span className="text-[10px] text-slate-500 uppercase tracking-widest">Pro workspace</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};
