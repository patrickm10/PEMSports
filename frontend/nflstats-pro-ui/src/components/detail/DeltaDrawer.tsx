import { X } from 'lucide-react';

interface DeltaDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  playerData?: any;
}

export function DeltaDrawer({ isOpen, onClose, playerData }: DeltaDrawerProps) {
  if (!isOpen) return null;

  return (
    <aside className="absolute inset-y-0 right-0 w-96 bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col p-6 animate-in slide-in-from-right duration-300">
      <div className="flex items-center justify-between mb-8">
        <h3 className="text-xl font-bold text-accent-blue tracking-tight">Insights</h3>
        <button 
          onClick={onClose}
          className="p-1 hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-white"
        >
          <X size={24} />
        </button>
      </div>

      {playerData ? (
        <div className="space-y-6">
          <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
            <h4 className="text-2xl font-bold">{playerData.player_name}</h4>
            <div className="flex gap-2 mt-1">
              <span className="text-slate-400 font-medium uppercase text-xs tracking-widest">{playerData.pos}</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-400 font-medium uppercase text-xs tracking-widest">{playerData.team_abbr}</span>
            </div>
          </div>

          <div className="text-center py-20 border-2 border-dashed border-slate-800 rounded-xl">
            <p className="text-slate-500 italic">Visualizations Handover (Rendering Hub)</p>
          </div>
        </div>
      ) : (
        <p className="text-slate-500 italic">Select a player to view depth analysis.</p>
      )}
    </aside>
  );
}
