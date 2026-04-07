import { Outlet } from 'react-router-dom';
import { NavigationDock } from './NavigationDock';

export function Layout() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Structural Components */}
      <NavigationDock />
      
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {/* Header / Context Bar could go here */}
        <div className="h-14 border-b border-slate-800 flex items-center px-6 bg-slate-900/50 backdrop-blur-sm z-10">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-widest">
            V3 Workspace / Analysis Desk
          </h2>
        </div>

        {/* Dynamic Content */}
        <section className="flex-1 overflow-hidden">
          <Outlet />
        </section>

        {/* Delta Drawer will be inserted here via Context or Portal if needed */}
      </main>
    </div>
  );
}
