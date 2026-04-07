import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Trophy, 
  Users, 
  Activity, 
  Target, 
  Shield, 
  Settings,
  ChevronRight,
  ChevronLeft
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const POSITIONS = [
  { id: 'QB', icon: Trophy, label: 'Quarterbacks' },
  { id: 'RB', icon: Users, label: 'Running Backs' },
  { id: 'WR', icon: Target, label: 'Wide Receivers' },
  { id: 'TE', icon: Target, label: 'Tight Ends' },
  { id: 'K', icon: Activity, label: 'Kickers' },
  { id: 'DST', icon: Shield, label: 'Defense/ST' },
];

export function NavigationDock() {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  return (
    <aside 
      className={cn(
        "h-screen bg-slate-900 border-r border-slate-800 transition-all duration-300 flex flex-col",
        isExpanded ? "w-64" : "w-16"
      )}
    >
      <div className="p-4 flex items-center justify-between border-b border-slate-800">
        {isExpanded && <span className="font-bold text-accent-blue tracking-tighter text-xl">NFLPro V3</span>}
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-slate-800 rounded-md transition-colors"
        >
          {isExpanded ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      <nav className="flex-1 py-4 px-2 space-y-2 overflow-y-auto">
        {POSITIONS.map((pos) => (
          <NavLink
            key={pos.id}
            to={`/rankings/${pos.id}`}
            className={({ isActive }) => cn(
              "flex items-center gap-3 p-3 rounded-lg transition-all group",
              isActive 
                ? "bg-accent-blue/10 text-accent-blue border border-accent-blue/20" 
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            )}
          >
            <pos.icon size={20} className={cn("flex-shrink-0 transition-transform group-hover:scale-110")} />
            {isExpanded && <span className="font-medium">{pos.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <button className={cn(
          "flex items-center gap-3 p-3 text-slate-400 hover:text-white transition-colors w-full rounded-lg",
          !isExpanded && "justify-center"
        )}>
          <Settings size={20} />
          {isExpanded && <span>Settings</span>}
        </button>
      </div>
    </aside>
  );
}
