import { LayoutDashboard, Database, Settings, Shield, Target, Zap, Crosshair, Activity, Trophy } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
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
}

const SidebarItem = ({ icon: Icon, label, active, onClick }: SidebarItemProps) => (
  <div 
    onClick={onClick}
    className={cn(
    "flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 group hover:bg-[#38bdf81a]",
    active ? "bg-[#38bdf81a] text-[#38bdf8] border border-[#38bdf833]" : "text-slate-400 hover:text-slate-200 border border-transparent"
  )}>
    <Icon size={18} className={cn("transition-transform group-hover:scale-110", active && "text-[#38bdf8]")} />
    <span className="text-sm font-medium tracking-wide">{label}</span>
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
}

export const Sidebar = ({ activePosition, onPositionChange }: SidebarProps) => {
  return (
    <div className="w-64 h-full bg-[#020617] border-r border-[#1e293b] p-4 flex flex-col gap-8 shadow-[10px_0px_30px_rgba(0,0,0,0.5)] z-20">
      <div className="flex items-center gap-3 px-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#38bdf8] to-[#0ea5e9] flex items-center justify-center shadow-[0px_0px_15px_#38bdf84d]">
          <Shield className="text-white" size={18} />
        </div>
        <h1 className="font-bold text-xl tracking-tight text-white italic">
          NFLStats <span className="text-[#38bdf8]">PRO</span>
        </h1>
      </div>

      <div className="flex flex-col gap-4">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3">
          Analysis Workspace
        </div>
        <div className="flex flex-col gap-1">
          <SidebarItem icon={LayoutDashboard} label="Dashboard" active={true} />
          <SidebarItem icon={Database} label="Data Source" />
          <SidebarItem icon={Settings} label="Config" />
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-3">
          Positional Entry
        </div>
        <div className="flex flex-col gap-1">
          {positions.map((pos) => (
            <SidebarItem
              key={pos.id}
              icon={pos.icon}
              label={pos.label}
              active={activePosition === pos.id}
              onClick={() => onPositionChange(pos.id)}
            />
          ))}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-[#1e293b]">
        <div className="flex items-center gap-3 px-3 py-4 bg-[#1e293b4d] rounded-xl border border-[#ffffff0a]">
          <div className="w-9 h-9 rounded-full bg-slate-800" />
          <div className="flex flex-col">
            <span className="text-sm font-bold text-slate-200">Engineer</span>
            <span className="text-xs text-slate-500 uppercase tracking-tighter">Foundation</span>
          </div>
        </div>
      </div>
    </div>
  );
};

