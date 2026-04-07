import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Zap, TrendingUp, Info } from 'lucide-react';
import { clsx } from 'clsx';

interface InsightData {
  player_id: string;
  player_name: string;
  predicted_alpha: number;
  smart_projection: number;
  insight_flags: string[];
}

interface ProInsightsDrawerProps {
  player: InsightData | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ProInsightsDrawer: React.FC<ProInsightsDrawerProps> = ({ player, isOpen, onClose }) => {
  if (!player) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop Blur Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
          />

          {/* Slide-over Drawer */}
          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.5 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full max-w-md bg-slate-900/90 backdrop-blur-2xl border-l border-white/10 shadow-2xl p-0 z-[101] overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10 bg-white/5">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-500/20 rounded-lg">
                  <Zap className="text-amber-400" size={20} />
                </div>
                <h2 className="text-xl font-semibold text-white">Pro Analytics Alpha</h2>
              </div>
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                aria-label="Close insights"
              >
                <X className="text-slate-400" size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="p-8 space-y-8 overflow-y-auto h-[calc(100vh-80px)]">
              {/* Player Summary */}
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-widest text-slate-400 font-bold">Current Situational Alpha</p>
                <h3 className="text-3xl font-bold text-white tracking-tight">{player.player_name}</h3>
              </div>

              {/* Alpha Delta Scoreboard */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-5 rounded-2xl bg-white/5 border border-white/5 space-y-1">
                  <span className="text-xs text-slate-400 font-medium">Smart Projection</span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-white">{player.smart_projection.toFixed(1)}</span>
                    <span className="text-xs text-slate-500 font-medium">FPTS</span>
                  </div>
                </div>
                <div className={clsx(
                  "p-5 rounded-2xl border space-y-1",
                  player.predicted_alpha >= 0 ? "bg-emerald-500/10 border-emerald-500/20" : "bg-rose-500/10 border-rose-500/20"
                )}>
                  <span className="text-xs text-slate-400 font-medium tracking-tight">Alpha Deviation</span>
                  <div className="flex items-center gap-2">
                    <span className={clsx(
                      "text-2xl font-bold",
                      player.predicted_alpha >= 0 ? "text-emerald-400" : "text-rose-400"
                    )}>
                      {player.predicted_alpha >= 0 ? '+' : ''}{player.predicted_alpha.toFixed(1)}
                    </span>
                    <TrendingUp className={clsx(
                      "size-5",
                      player.predicted_alpha >= 0 ? "text-emerald-400" : "text-rose-400 -rotate-90"
                    )} />
                  </div>
                </div>
              </div>

              {/* SHAP Insights (Explainability) */}
              <div className="space-y-5">
                <div className="flex items-center gap-2">
                  <Info className="text-amber-400/80" size={16} />
                  <h4 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Predictive Indicators</h4>
                </div>
                
                <div className="space-y-3">
                  {player.insight_flags.length > 0 ? (
                    player.insight_flags.map((flag, idx) => (
                      <motion.div 
                        key={idx}
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] transition-all group"
                      >
                        <div className="size-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)] group-hover:scale-125 transition-transform" />
                        <span className="text-sm font-medium text-slate-300">{flag}</span>
                      </motion.div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 italic">No significant situational anomalies detected for this matchup.</p>
                  )}
                </div>
              </div>

              {/* Methodology Footer */}
              <div className="pt-8 border-t border-white/5">
                <p className="text-[10px] text-slate-600 leading-relaxed max-w-[280px]">
                  Alpha values represent situational deviations from baseline season performance. Calculated via localized positional models (v1.2.0) with SHAP feature weight explanation.
                </p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
