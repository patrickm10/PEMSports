import React, { useRef, useState } from 'react';
import { Mail, Lock, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { Modal } from '../../../v3/components/modals/Modal';

interface LoginModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

const HONEST_DESCRIPTION =
  'Signing in does not change the rankings or analytics you can view.';

export function LoginModal({ onClose, onSuccess }: LoginModalProps) {
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
      setError('Please fill in all fields.');
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
      let msg = isRegistering ? 'Registration failed.' : 'Invalid email or password.';
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
      setError(msg || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen
      onClose={onClose}
      size="sm"
      title={isRegistering ? 'Create account' : 'Sign in'}
      description={HONEST_DESCRIPTION}
      initialFocusRef={emailRef as React.RefObject<HTMLElement | null>}
      contentClassName="px-6 pb-6 pt-2"
    >
      {error && (
        <div
          className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0" aria-hidden />
          <p className="text-left">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div className="space-y-1.5">
          <label htmlFor="pem-auth-email" className="text-sm font-medium text-slate-300">
            Email Address
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Mail className="h-5 w-5" aria-hidden />
            </div>
            <input
              id="pem-auth-email"
              ref={emailRef}
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="block w-full pl-10 pr-3 py-2.5 bg-slate-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-200 sm:text-sm transition-colors"
              placeholder="you@example.com"
              required
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label htmlFor="pem-auth-password" className="text-sm font-medium text-slate-300">
            Password
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Lock className="h-5 w-5" aria-hidden />
            </div>
            <input
              id="pem-auth-password"
              type="password"
              autoComplete={isRegistering ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full pl-10 pr-3 py-2.5 bg-slate-900 border border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-slate-200 sm:text-sm transition-colors"
              placeholder="••••••••"
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center py-2.5 px-4 rounded-lg shadow-sm text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors mt-6"
        >
          {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden />}
          {isRegistering ? 'Create Account' : 'Sign In'}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-400">
        {isRegistering ? 'Already have an account?' : "Don't have an account?"}{' '}
        <button
          type="button"
          onClick={() => {
            setIsRegistering(!isRegistering);
            setError('');
          }}
          className="font-medium text-blue-500 hover:text-blue-400 hover:underline transition-colors focus-visible:ring-2 focus-visible:ring-blue-400 rounded"
        >
          {isRegistering ? 'Sign in' : 'Create one'}
        </button>
      </p>
    </Modal>
  );
}
