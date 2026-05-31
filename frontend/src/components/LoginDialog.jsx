import { useEffect, useState } from 'react';
import { useAuth } from '../providers/AuthProvider';
import { BrandMark } from './BrandMark';
import { Loader2, Mail, KeyRound, ArrowRight, X } from 'lucide-react';


/**
 * LoginDialog — modal overlay opened on demand (sending a message, the
 * sidebar "Sign in" button, etc.). Dismissible via the X button or the
 * Escape key. Self-closes once a session is established.
 */
export function LoginDialog() {
  const {
    signInPassword,
    signUpPassword,
    error,
    clearError,
    loginDialogMode,
    closeLoginDialog,
  } = useAuth();

  const [mode, setMode] = useState(loginDialogMode || 'signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [info, setInfo] = useState(null);

  // Sync local mode with whatever the trigger asked for (sign in vs sign up).
  useEffect(() => { setMode(loginDialogMode || 'signin'); }, [loginDialogMode]);

  // Esc to dismiss.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') closeLoginDialog(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [closeLoginDialog]);

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setSubmitting(true);
    setInfo(null);
    clearError();
    try {
      if (mode === 'signin') {
        await signInPassword({ email: email.trim(), password });
      } else {
        await signUpPassword({ email: email.trim(), password });
        setInfo("Check your inbox for a confirmation link. (Or disable email confirmation in Supabase Auth → Settings for a no-friction demo.)");
      }
    } catch {
      /* error surfaced via AuthProvider */
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-background/80 backdrop-blur-md"
      onClick={(e) => { if (e.target === e.currentTarget) closeLoginDialog(); }}
    >
      <div
        className="relative w-full max-w-md rounded-lg border border-border bg-card shadow-[0_20px_60px_-20px_rgba(138,42,43,0.35)] overflow-hidden"
      >
        {/* Close */}
        <button
          type="button"
          onClick={closeLoginDialog}
          className="absolute right-3 top-3 h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          title="Close"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Masthead */}
        <div className="px-7 pt-7 pb-5 text-center">
          <div className="flex justify-center mb-3">
            <BrandMark size={40} tone="duo" strokeWidth={1.4} />
          </div>
          <p className="font-brand text-[11px] uppercase tracking-[0.3em] text-muted-foreground/70 select-none">
            Brandmate
          </p>
          <h1 className="font-brand text-3xl font-semibold tracking-tight text-foreground mt-1.5">
            {mode === 'signin' ? (
              <>Welcome <span className="font-brand-italic text-primary">back</span></>
            ) : (
              <>Join the <span className="font-brand-italic text-primary">atelier</span></>
            )}
          </h1>
          <p className="mt-1.5 font-brand-italic text-[13px] text-muted-foreground">
            {mode === 'signin'
              ? 'Sign in to pick up where you left off.'
              : 'Create a Brandmate account to start your collection.'}
          </p>
          <hr className="rule-double mt-4 mx-auto w-24" />
        </div>

        <div className="px-7 pb-7">
          {/* Mode toggle */}
          <div className="flex items-center justify-center gap-1 mb-5 text-[12px] font-brand uppercase tracking-[0.18em]">
            <button
              type="button"
              onClick={() => { setMode('signin'); setInfo(null); clearError(); }}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                mode === 'signin'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setInfo(null); clearError(); }}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                mode === 'signup'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Sign up
            </button>
          </div>

          {/* Form */}
          <form onSubmit={onSubmit} className="space-y-3">
            <label className="block">
              <span className="font-brand text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Email</span>
              <div className="mt-1 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/70" />
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@studio.com"
                  className="w-full rounded-md border border-border bg-input pl-9 pr-3 py-2 text-[14px] text-foreground placeholder:text-muted-foreground/60 outline-none focus:border-ring/70 transition-colors"
                />
              </div>
            </label>

            <label className="block">
              <span className="font-brand text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Password</span>
              <div className="mt-1 relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/70" />
                <input
                  type="password"
                  autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-md border border-border bg-input pl-9 pr-3 py-2 text-[14px] text-foreground placeholder:text-muted-foreground/60 outline-none focus:border-ring/70 transition-colors"
                />
              </div>
            </label>

            {error && (
              <p className="text-[12px] text-destructive font-brand-italic">{error}</p>
            )}
            {info && (
              <p className="text-[12px] text-muted-foreground font-brand-italic">{info}</p>
            )}

            <button
              type="submit"
              disabled={submitting || !email.trim() || !password}
              className="send-btn w-full h-10 rounded-md flex items-center justify-center gap-2 text-[14px] font-medium"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  {mode === 'signin' ? 'Enter' : 'Create account'}
                  <ArrowRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          <p className="mt-5 text-center font-brand-italic text-[11px] text-muted-foreground/70">
            By continuing you agree to the studio's terms — be kind, be brand-safe.
          </p>
        </div>
      </div>
    </div>
  );
}
