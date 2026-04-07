import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from '../navigation/Sidebar';
import { ChevronRight, ChevronLeft, LayoutDashboard, Shield } from 'lucide-react';

interface ResponsiveDockProps {
  children: React.ReactNode;
  rightPane?: React.ReactNode;
  activePosition: string;
  onPositionChange: (pos: string) => void;
}

export const ResponsiveDock = ({ 
  children, 
  rightPane, 
  activePosition, 
  onPositionChange 
}: ResponsiveDockProps) => {
  const [isRightPaneOpen, setIsRightPaneOpen] = useState(true);

  return (
    <div className="flex h-screen w-full bg-[#020617] text-slate-200 overflow-hidden font-outfit">
      {/* 1. Fixed Navigation Sidebar (Left) */}
      <Sidebar activePosition={activePosition} onPositionChange={onPositionChange} />

      {/* 2. Virtualized Analysis Desk (Center) */}
      <main className="flex-1 flex flex-col h-full bg-[#020617] overflow-hidden relative">
        <header className="h-16 border-b border-[#1e293b] flex items-center justify-between px-8 bg-[#020617b3] backdrop-blur-xl z-10">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-semibold tracking-[0.2em] uppercase text-slate-500">
              Analysis <span className="text-[#38bdf8]">Workspace</span>
            </h2>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsRightPaneOpen(!isRightPaneOpen)}
              className="p-2 hover:bg-[#1e293b] rounded-lg transition-colors border border-[#1e293b]"
            >
              <LayoutDashboard size={18} className="text-[#38bdf8]" />
            </button>
          </div>
        </header>

        <section className="flex-1 overflow-y-auto p-8 relative scrollbar-thin scrollbar-thumb-[#1e293b] scrollbar-track-transparent">
          {children}
        </section>

        {/* Glossy Backdrop Decoration */}
        <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-[#38bdf805] blur-[120px] rounded-full -z-0 pointer-events-none" />
      </main>

      {/* 3. Action/Insight Drawer (Right) */}
      <AnimatePresence>
        {isRightPaneOpen && (
          <motion.aside
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="w-96 h-full bg-[#020617] border-l border-[#1e293b] p-6 z-20 flex flex-col gap-6 shadow-[[-20px_0px_50px_rgba(0,0,0,0.4)]]"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold tracking-widest text-[#38bdf8] uppercase">
                Delta <span className="text-slate-400">Insights</span>
              </h3>
              <button 
                onClick={() => setIsRightPaneOpen(false)}
                className="text-slate-500 hover:text-slate-200 transition-colors"
                title="Collapse Drawer"
              >
                <ChevronRight size={18} />
              </button>
            </div>

            <div className="flex-1 bg-[#1e293b4d] rounded-2xl border border-[#ffffff0a] p-4 flex flex-col gap-4 overflow-y-auto">
              {rightPane || (
                <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-40">
                  <Shield size={48} className="mb-4" />
                  <p className="text-sm font-medium">Select a data entry to view contextual analysis.</p>
                </div>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Floating Expand Tab when Right Pane is closed */}
      {!isRightPaneOpen && (
        <button 
          onClick={() => setIsRightPaneOpen(true)}
          className="fixed right-0 top-1/2 -translate-y-1/2 w-8 h-20 bg-[#1e293b] border-l border-y border-[#38bdf84d] rounded-l-xl flex items-center justify-center transition-all hover:w-10 group z-30"
          title="Expand Insights"
        >
          <ChevronLeft size={20} className="text-[#38bdf8] group-hover:scale-125 transition-transform" />
        </button>
      )}
    </div>
  );
};
