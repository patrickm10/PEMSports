import React, { useRef, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { Modal } from '../../../v3/components/modals/Modal';

interface LoginModalProps {
  onClose: () => void;
  onSuccess?: () => void;
  onContinueAsGuest?: () => void;
}

export function LoginModal({
  onClose,
  onSuccess,
  onContinueAsGuest,
}: LoginModalProps) {
  const { login, register } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Enter an email and password.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      if (isRegistering) {
        await register({ email, password });
      } else {
        await login({ email, password });
      }
      onSuccess?.();
      onClose();
    } catch (err: unknown) {
      let msg = isRegistering ? 'Could not create the account.' : 'Email or password is incorrect.';
      if (err && typeof err === 'object' && 'response' in err) {
        const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
        if (typeof detail === 'string') {
          msg = detail;
        } else if (
          Array.isArray(detail) &&
          detail[0] &&
          typeof detail[0] === 'object' &&
          detail[0] !== null &&
          'msg' in detail[0]
        ) {
          msg = String((detail[0] as { msg: unknown }).msg);
        }
      }
      setError(msg || 'Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const title = isRegistering ? 'Create account' : 'Sign in';

  return (
    <Modal
      isOpen
      onClose={onClose}
      size="sm"
      title={title}
      initialFocusRef={emailRef as React.RefObject<HTMLElement | null>}
      contentClassName="px-6 pb-7 pt-1"
    >
      {error && (
        <div
          className="mb-4 flex items-start gap-2 rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-300"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <p>{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-4 space-y-4 text-left">
        <div className="space-y-1.5">
          <label htmlFor="pem-auth-email" className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Email
          </label>
          <input
            id="pem-auth-email"
            ref={emailRef}
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="block w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-600 transition-colors focus:border-sky-500/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40"
            placeholder="you@example.com"
            required
          />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="pem-auth-password" className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Password
          </label>
          <input
            id="pem-auth-password"
            type="password"
            autoComplete={isRegistering ? 'new-password' : 'current-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="block w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-600 transition-colors focus:border-sky-500/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40"
            placeholder="••••••••"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 flex w-full items-center justify-center rounded-xl bg-sky-500 py-3 text-sm font-bold uppercase tracking-wider text-white shadow-[0_12px_28px_rgba(56,189,248,0.25)] transition-colors hover:bg-sky-400 focus-visible:ring-2 focus-visible:ring-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
          {isRegistering ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-slate-400">
        {isRegistering ? 'Already have an account?' : 'New here?'}{' '}
        <button
          type="button"
          onClick={() => {
            setIsRegistering(!isRegistering);
            setError('');
          }}
          className="font-semibold text-sky-400 hover:text-sky-300 focus-visible:ring-2 focus-visible:ring-sky-400 rounded"
        >
          {isRegistering ? 'Sign in' : 'Create an account'}
        </button>
      </p>

      {onContinueAsGuest && (
        <button
          type="button"
          onClick={() => {
            onClose();
            onContinueAsGuest();
          }}
          className="mt-3 w-full py-2 text-center text-sm font-medium text-slate-500 hover:text-slate-300"
        >
          Skip — enter as guest
        </button>
      )}
    </Modal>
  );
}
