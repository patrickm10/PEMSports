import type { ReactNode } from 'react';
import { V3ContextBar } from './V3ContextBar';
import { LucideLayoutDashboard, LucideSettings, LucideDatabase, LucideActivity } from 'lucide-react';

interface V3WorkspaceLayoutProps {
  children: ReactNode;
  drawer?: ReactNode;
}

export function V3WorkspaceLayout({ children, drawer }: V3WorkspaceLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-[#020617] text-[#f8fafc] font-sans selection:bg-blue-500/30">
      {/* Mini Sidebar (V3 Style) */}
      <aside className="w-16 flex flex-col items-center py-6 gap-8 border-r border-white/5 bg-[#0f172a]/50 backdrop-blur-xl">
        <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-900/20">
          <LucideDatabase className="w-6 h-6 text-white" />
        </div>
        
        <nav className="flex flex-col gap-6 flex-1">
          <button className="p-2.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 transition-all">
            <LucideLayoutDashboard className="w-5 h-5" />
          </button>
          <button className="p-2.5 rounded-lg text-slate-500 hover:text-slate-300 transition-all">
            <LucideActivity className="w-5 h-5" />
          </button>
        </nav>

        <button className="p-2.5 rounded-lg text-slate-500 hover:text-slate-300 transition-all">
          <LucideSettings className="w-5 h-5" />
        </button>
      </aside>

      {/* Main Analysis Console */}
      <main className="flex-1 flex flex-col relative h-full">
        {/* Sticky Global Context Bar */}
        <V3ContextBar />

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Scrollable Working Grid */}
          <section className="flex-1 overflow-auto custom-scrollbar">
            {children}
          </section>

          {/* Persistent Focus Drawer (The Delta Analysis Desk) */}
          {drawer && (
            <aside className="w-96 border-l border-white/5 bg-[#0f172a]/20 backdrop-blur-2xl shadow-2xl z-10 overflow-auto custom-scrollbar">
              {drawer}
            </aside>
          )}
        </div>
      </main>
    </div>
  );
}
