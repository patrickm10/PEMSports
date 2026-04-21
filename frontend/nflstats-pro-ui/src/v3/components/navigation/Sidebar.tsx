import { 
  LayoutDashboard, 
  Database, 
  Settings, 
  Shield, 
  Target, 
  Zap, 
  Crosshair, 
  Activity, 
  Trophy,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface SidebarItemProps {
  icon: LucideIcon;
  label: string;
  active?: boolean;
  onClick?: () => void;
  collapsed?: boolean;
}

const SidebarItem = ({ icon: Icon, label, active, onClick, collapsed }: SidebarItemProps) => (
  <div 
    onClick={onClick}
    className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 group hover:bg-[#38bdf81a] relative",
      active ? "bg-[#38bdf81a] text-[#38bdf8] border border-[#38bdf833]" : "text-slate-400 hover:text-slate-200 border border-transparent",
      collapsed && "justify-center px-0"
    )}
    title={collapsed ? label : undefined}
  >
    <Icon size={18} className={cn("transition-transform group-hover:scale-110 shrink-0", active && "text-[#38bdf8]")} />
    <AnimatePresence>
      {!collapsed && (
        <motion.span 
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
          className="text-sm font-medium tracking-wide whitespace-nowrap overflow-hidden"
        >
          {label}
        </motion.span>
      )}
    </AnimatePresence>
  </div>
);

const positions = [
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
}

export const Sidebar = ({ activePosition, onPositionChange, collapsed, onToggle }: SidebarProps) => {
  return (
    <motion.div 
      initial={false}
      animate={{ width: collapsed ? 80 : 210 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="h-full bg-[#020617] border-r border-[#1e293b] py-6 flex flex-col gap-8 shadow-[10px_0px_30px_rgba(0,0,0,0.5)] z-20 relative overflow-hidden"
    >
      {/* Sidebar Toggle Button */}
      <button 
        onClick={onToggle}
        className="absolute -right-3 top-12 w-6 h-6 bg-[#1e293b] border border-[#38bdf833] rounded-full flex items-center justify-center text-[#38bdf8] hover:bg-[#38bdf81a] transition-colors z-30 shadow-lg"
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Logo */}
      <div className={cn("flex items-center gap-3 px-6 overflow-hidden shrink-0", collapsed && "px-0 justify-center")}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#0ea5e9] flex items-center justify-center shadow-[0px_0px_15px_#38bdf84d] shrink-0">
          <Shield className="text-white" size={18} />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.h1 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="font-bold text-xl tracking-tight text-white italic whitespace-nowrap"
            >
              NFLStats <span className="text-[#38bdf8]">PRO</span>
            </motion.h1>
          )}
        </AnimatePresence>
      </div>

      <div className="flex flex-col gap-6 flex-1 px-4 overflow-y-auto no-scrollbar">
        {/* Workspace Group */}
        <div className="flex flex-col gap-4">
          {!collapsed && (
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3">
              Analysis Workspace
            </div>
          )}
          <div className="flex flex-col gap-1">
            <SidebarItem icon={LayoutDashboard} label="Dashboard" active={true} collapsed={collapsed} />
            <SidebarItem icon={Database} label="Data Source" collapsed={collapsed} />
            <SidebarItem icon={Settings} label="Config" collapsed={collapsed} />
          </div>
        </div>

        {/* Positions Group */}
        <div className="flex flex-col gap-4">
          {!collapsed && (
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3">
              Positional Entry
            </div>
          )}
          <div className="flex flex-col gap-1">
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
          </div>
        </div>
      </div>

      {/* Footer Profile */}
      <div className="px-4 shrink-0">
        <div className={cn(
          "flex items-center gap-3 p-3 bg-[#1e293b4d] rounded-xl border border-[#ffffff0a] transition-all overflow-hidden",
          collapsed && "justify-center p-2"
        )}>
          <div className="w-8 h-8 rounded-full bg-slate-800 shrink-0 border border-[#38bdf822]" />
          <AnimatePresence>
            {!collapsed && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col"
              >
                <span className="text-sm font-bold text-slate-200">Engineer</span>
                <span className="text-[10px] text-slate-600 uppercase tracking-widest">Foundation</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};
