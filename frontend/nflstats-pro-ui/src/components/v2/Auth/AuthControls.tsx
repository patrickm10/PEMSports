import { useState } from 'react';
import { LogOut, User } from 'lucide-react';
import { persistLandingSkip } from '../../../utils/filterState';
import { useAuth } from '../../../contexts/AuthContext';
import { LoginModal } from './LoginModal';

export function AuthControls() {
  const { user, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [authMenuOpen, setAuthMenuOpen] = useState(false);

  return (
    <>
      {user ? (
        <div className="relative">
          <button
            type="button"
            aria-expanded={authMenuOpen}
            aria-haspopup="menu"
            onClick={() => setAuthMenuOpen((o) => !o)}
            onBlur={() => {
              window.setTimeout(() => setAuthMenuOpen(false), 150);
            }}
            className="inline-flex items-center gap-2 h-10 sm:h-11 pl-3 pr-1.5 rounded-xl bg-slate-950/40 border border-white/[0.04] text-sm font-semibold text-slate-300 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-blue-500/50"
          >
            <span className="truncate max-w-[100px]">{user.email.split('@')[0]}</span>
            <div className="bg-blue-600/20 text-blue-400 p-1.5 rounded-lg">
              <User className="w-4 h-4" aria-hidden />
            </div>
          </button>
          {authMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full mt-2 w-48 py-1 rounded-xl bg-slate-800 border border-slate-700 shadow-xl z-20"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setAuthMenuOpen(false);
                  logout();
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-slate-700/50 transition-colors text-left"
              >
                <LogOut className="w-4 h-4" aria-hidden />
                Sign Out
              </button>
            </div>
          )}
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setShowLogin(true)}
          className="inline-flex items-center gap-2 h-10 sm:h-11 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-sm font-bold text-white transition-colors shadow-lg shadow-blue-500/20 whitespace-nowrap focus-visible:ring-2 focus-visible:ring-blue-300"
        >
          <User className="w-4 h-4" aria-hidden />
          Sign In
        </button>
      )}

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onSuccess={persistLandingSkip}
        />
      )}
    </>
  );
}
