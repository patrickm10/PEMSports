import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Trophy,
  ChevronRight,
  ChevronLeft,
  LayoutDashboard,
  Shield,
  Activity,
  Target,
  Crosshair,
  Zap,
} from 'lucide-react';
import { cn } from '../../utils/cn';

interface SidebarItemProps {
  icon: React.ElementType;
  label: string;
  active?: boolean;
  onClick?: () => void;
  collapsed?: boolean;
}

const SidebarItem: React.FC<SidebarItemProps> = ({
  icon: Icon, label, active, onClick, collapsed,
}) => (
  <button
    onClick={onClick}
    className={cn(
      "flex items-center gap-3 w-full px-4 py-3 rounded-xl transition-all duration-200 group relative",
      active
        ? "bg-blue-600/15 text-blue-400 border border-blue-500/25 shadow-[0_0_20px_rgba(59,130,246,0.08)]"
        : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200 border border-transparent"
    )}
  >
    <Icon className={cn(
      "w-5 h-5 shrink-0 transition-transform duration-200",
      active ? "scale-110" : "group-hover:scale-105"
    )} />
    <AnimatePresence>
      {!collapsed && (
        <motion.span
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 'auto' }}
          exit={{ opacity: 0, width: 0 }}
          className="font-medium whitespace-nowrap overflow-hidden text-sm"
        >
          {label}
        </motion.span>
      )}
    </AnimatePresence>
    {collapsed && (
      <div className="absolute left-full ml-3 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 shadow-xl">
        {label}
      </div>
    )}
  </button>
);

interface DashboardV2Props {
  children: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
  isDarkMode?: boolean;
}

const positions = [
  { id: 'qb', label: 'Quarterbacks', icon: Crosshair },
  { id: 'rb', label: 'Running Backs', icon: Zap },
  { id: 'wr', label: 'Wide Receivers', icon: Target },
  { id: 'te', label: 'Tight Ends', icon: Activity },
  { id: 'k', label: 'Kickers', icon: Trophy },
  { id: 'dst', label: 'Defense/ST', icon: Shield },
];

export const DashboardV2: React.FC<DashboardV2Props> = ({
  children, activePosition, onPositionChange,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100 font-sans">
      {/* ── Sidebar ──────────────────────────────────────────────── */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 80 : 260 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
        className="fixed top-0 left-0 h-screen bg-slate-900/60 backdrop-blur-2xl border-r border-slate-800/40 flex flex-col z-50"
      >
        {/* Logo */}
        <div className="p-5 flex items-center justify-between overflow-hidden">
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2.5"
              >
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/20">
                  <LayoutDashboard className="w-5 h-5 text-white" />
                </div>
                <span className="font-bold text-lg tracking-tight">
                  NFLStats<span className="text-blue-400">PRO</span>
                </span>
              </motion.div>
            )}
          </AnimatePresence>
          {collapsed && (
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-500/20 mx-auto">
              <LayoutDashboard className="w-5 h-5 text-white" />
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "mx-4 mb-2 p-1.5 rounded-lg hover:bg-slate-800/50 text-slate-500 hover:text-slate-300 transition-colors self-end",
            collapsed && "self-center"
          )}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          <div className={cn(
            "text-[10px] font-semibold text-slate-600 uppercase tracking-[0.15em] mb-3 px-3",
            collapsed && "text-center"
          )}>
            {collapsed ? "POS" : "Positions"}
          </div>
          {positions.map((pos) => (
            <SidebarItem
              key={pos.id}
              icon={pos.icon}
              label={pos.label}
              active={activePosition === pos.id}
              onClick={() => onPositionChange(pos.id)}
              collapsed={collapsed}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800/30">
          <div className={cn(
            "text-[10px] text-slate-600 text-center",
            collapsed && "hidden"
          )}>
            v2.0 · Schema Validated
          </div>
        </div>
      </motion.aside>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <main className={cn(
        "flex-1 transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
        collapsed ? "pl-20" : "pl-[260px]"
      )}>
        <div className="max-w-[1700px] mx-auto p-6 lg:p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={activePosition}
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: -16, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};
