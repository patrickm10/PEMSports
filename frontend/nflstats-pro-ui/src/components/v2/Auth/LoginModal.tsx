import React, { useRef, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { AuthApiError } from '../../../models/Auth';
import { Modal } from '../../../v3/components/modals/Modal';

interface LoginModalProps {
  onClose: () => void;
  onSuccess?: () => void;
  onContinueAsGuest?: () => void;
}

function errorMessage(err: unknown, isRegistering: boolean): string {
  if (err instanceof AuthApiError && err.detail) {
    return err.detail;
  }
  return isRegistering ? 'Could not create the account.' : 'Email or password is incorrect.';
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

  const switchMode = (registering: boolean) => {
    setIsRegistering(registering);
    setError('');
    setPassword('');
    requestAnimationFrame(() => emailRef.current?.focus());
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Enter an email and password.');
      return;
    }
    if (isRegistering && password.length < 8) {
      setError('Use at least 8 characters for the password.');
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
      setError(errorMessage(err, isRegistering) || 'Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const title = isRegistering ? 'Create account' : 'Sign in';
  const invalid = Boolean(error);

  return (
    <Modal
      isOpen
      onClose={onClose}
      size="sm"
      title={title}
      initialFocusRef={emailRef as React.RefObject<HTMLElement | null>}
      className="max-h-[min(90dvh,40rem)] overflow-y-auto"
      contentClassName="px-6 pb-7 pt-1"
    >
      <div
        className="mb-5 grid grid-cols-2 gap-1 rounded-xl border border-white/10 bg-slate-950/80 p-1"
        role="tablist"
        aria-label="Sign in or create account"
      >
        <button
          type="button"
          role="tab"
          aria-selected={!isRegistering}
          onClick={() => switchMode(false)}
          className={`min-h-11 rounded-lg px-3 text-sm font-bold transition-colors focus-visible:ring-2 focus-visible:ring-sky-400 ${
            !isRegistering
              ? 'bg-sky-500 text-white'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={isRegistering}
          onClick={() => switchMode(true)}
          className={`min-h-11 rounded-lg px-3 text-sm font-bold transition-colors focus-visible:ring-2 focus-visible:ring-sky-400 ${
            isRegistering
              ? 'bg-sky-500 text-white'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Create account
        </button>
      </div>

      <p className="mb-6 text-sm leading-relaxed text-slate-400">
        An account is optional identity. Rankings and analytics are the same
        whether you sign in or continue as a guest.
      </p>

      {error && (
        <div
          className="mb-4 flex items-start gap-2 rounded-xl border border-red-500/25 bg-red-500/10 p-3 text-sm text-red-300"
          role="alert"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <p>{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-left">
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
            aria-invalid={invalid}
            className="block min-h-11 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-600 transition-colors focus:border-sky-500/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40"
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
            aria-invalid={invalid}
            aria-describedby={isRegistering ? 'pem-auth-password-hint' : undefined}
            className="block min-h-11 w-full rounded-xl border border-white/10 bg-slate-950/80 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-600 transition-colors focus:border-sky-500/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-500/40"
            placeholder="••••••••"
            required
          />
          {isRegistering && (
            <p id="pem-auth-password-hint" className="text-xs text-slate-500">
              At least 8 characters.
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-2 flex min-h-11 w-full items-center justify-center rounded-xl bg-sky-500 py-3 text-sm font-bold uppercase tracking-wider text-white shadow-[0_12px_28px_rgba(56,189,248,0.25)] transition-colors hover:bg-sky-400 focus-visible:ring-2 focus-visible:ring-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />}
          {isRegistering ? 'Create account' : 'Sign in'}
        </button>
      </form>

      {onContinueAsGuest && (
        <button
          type="button"
          onClick={() => {
            onClose();
            onContinueAsGuest();
          }}
          className="mt-3 min-h-11 w-full py-2.5 text-center text-sm font-medium text-slate-500 hover:text-slate-300"
        >
          Skip — enter as guest
        </button>
      )}
    </Modal>
  );
}
