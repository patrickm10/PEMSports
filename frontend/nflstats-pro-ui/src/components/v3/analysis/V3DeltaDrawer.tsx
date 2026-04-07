/**
 * V3 Delta Analysis Drawer
 * Persistent focus desk for entity deep-dives.
 * Dynamic contextual insights powered by situational stats.
 */

import { LucideCrosshair, LucideInfo, LucideLineChart, LucideTriangleAlert, LucideX } from 'lucide-react';

interface V3DeltaDrawerProps {
  id?: string;
  onClose: () => void;
}

export function V3DeltaDrawer({ id, onClose }: V3DeltaDrawerProps) {
  if (!id) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 text-center text-slate-500 opacity-60">
        <LucideCrosshair className="w-12 h-12 mb-4 animate-pulse" />
        <p className="text-xs uppercase font-black tracking-widest leading-loose">
          Awaiting Entity Focus<br />
          <span className="text-[10px] lowercase font-medium text-slate-600">Select an athlete from the grid to begin situational analysis</span>
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Drawer Header */}
      <header className="p-6 border-b border-white/5 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-slate-100 tracking-tight">Delta Desk</h2>
          <p className="text-[10px] text-blue-500 font-bold uppercase tracking-[0.2em] mt-1">Situational Analytics</p>
        </div>
        <button 
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-all"
        >
          <LucideX className="w-5 h-5" />
        </button>
      </header>

      {/* Analysis Content */}
      <div className="flex-1 overflow-auto p-6 space-y-8 custom-scrollbar">
        {/* Profile Card Placeholder */}
        <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0f172a] to-[#020617] border border-white/5 shadow-xl">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-14 h-14 rounded-full bg-slate-800 border-2 border-blue-500/30 flex items-center justify-center font-black text-slate-400">
              ?
            </div>
            <div>
              <p className="text-sm font-bold text-slate-300">Player ID: {id.slice(0, 8)}</p>
              <p className="text-xs text-slate-500">Retrieving intelligence...</p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-white/5 rounded-xl border border-white/5">
              <p className="text-[9px] text-slate-500 uppercase font-black mb-1">Stability</p>
              <p className="text-sm font-bold text-emerald-400">High</p>
            </div>
            <div className="p-3 bg-white/5 rounded-xl border border-white/5">
              <p className="text-[9px] text-slate-500 uppercase font-black mb-1">Volatilty</p>
              <p className="text-sm font-bold text-amber-400">Moderate</p>
            </div>
          </div>
        </div>

        {/* Delta Intelligence Segment */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-slate-300">
            <LucideLineChart className="w-4 h-4 text-blue-500" />
            <h3 className="text-xs font-black uppercase tracking-widest">Growth Vector</h3>
          </div>
          
          <div className="h-40 w-full bg-white/5 rounded-2xl border border-dashed border-white/10 flex items-center justify-center">
            <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest">Visualization Pending</p>
          </div>
        </section>

        {/* Situational Alerts */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 text-slate-300">
            <LucideTriangleAlert className="w-4 h-4 text-rose-500" />
            <h3 className="text-xs font-black uppercase tracking-widest">Situational Risks</h3>
          </div>
          
          <div className="p-4 rounded-xl bg-orange-500/5 border border-orange-500/10 flex gap-4">
            <LucideInfo className="w-5 h-5 text-orange-400 flex-shrink-0" />
            <p className="text-xs text-slate-400 leading-relaxed font-medium">
              Data suggests a potential performance regression in high-elevation indoor venues. <span className="text-orange-400 font-bold underline cursor-pointer">Analyze Matchups</span>
            </p>
          </div>
        </section>
      </div>

      {/* Drawer Footer Actions */}
      <footer className="p-6 border-t border-white/5 bg-[#0f172a]/40">
        <button className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-bold uppercase text-[10px] tracking-[0.2em] shadow-lg shadow-blue-900/20 transition-all">
          Generate Full Report
        </button>
      </footer>
    </div>
  );
}
