import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, X } from 'lucide-react';

type ToastKind = 'error' | 'info';

export type ToastPayload = {
  id: number;
  kind: ToastKind;
  title: string;
  message: string;
  code?: string;
};

type ToastContextValue = {
  showError: (message: string, code?: string) => void;
  showInfo: (message: string, code?: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastPayload[]>([]);

  const push = useCallback((kind: ToastKind, message: string, code?: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    const title = kind === 'error' ? 'Request failed' : 'Notice';
    setToasts((prev) => [...prev.slice(-4), { id, kind, title, message, code }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6500);
  }, []);

  const showError = useCallback(
    (message: string, code?: string) => {
      push('error', message, code);
    },
    [push],
  );

  const showInfo = useCallback(
    (message: string, code?: string) => {
      push('info', message, code);
    },
    [push],
  );

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo(() => ({ showError, showInfo }), [showError, showInfo]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-[200] flex w-[min(100%,22rem)] flex-col gap-2"
        aria-live="polite"
      >
        <AnimatePresence mode="popLayout">
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 420, damping: 32 }}
              className="pointer-events-auto rounded-xl border border-white/[0.1] bg-[rgba(15,23,42,0.92)] px-3 py-2.5 shadow-2xl backdrop-blur-xl"
            >
              <div className="flex gap-2">
                <AlertCircle
                  className={t.kind === 'error' ? 'mt-0.5 shrink-0 text-rose-400' : 'mt-0.5 shrink-0 text-sky-400'}
                  size={16}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{t.title}</p>
                  <p className="mt-0.5 text-sm leading-snug text-slate-100">{t.message}</p>
                  {t.code ? (
                    <p className="mt-1 font-mono text-[10px] tabular-nums text-slate-500">{t.code}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded-md p-1 text-slate-500 hover:bg-white/[0.06] hover:text-slate-300"
                  onClick={() => dismiss(t.id)}
                  aria-label="Dismiss notification"
                >
                  <X size={16} />
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
