import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { supabase } from '../lib/supabaseClient';

const AuthContext = createContext(null);

/**
 * AuthProvider — single source of truth for the current Supabase session
 * across the app. Wraps Supabase's onAuthStateChange so React stays in
 * sync with token refreshes and sign-outs.
 *
 * Also owns the open/closed state of the LoginDialog. The dialog is not
 * shown automatically on `!session` — instead, anything that requires
 * auth (sending a message, clicking the sidebar "Sign in" button) calls
 * `openLoginDialog()`. The dialog closes itself automatically once the
 * session becomes truthy.
 *
 * Exposes:
 *   session, user, loading, error
 *   signInPassword({email, password})
 *   signUpPassword({email, password})
 *   signOut()
 *   loginDialogOpen, openLoginDialog(mode?), closeLoginDialog()
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loginDialogOpen, setLoginDialogOpen] = useState(false);
  const [loginDialogMode, setLoginDialogMode] = useState('signin');
  const queryClient = useQueryClient();

  useEffect(() => {
    let cancelled = false;

    // 1) Hydrate from persisted session on mount.
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setSession(data.session ?? null);
      setLoading(false);
    });

    // 2) Subscribe to subsequent changes.
    const { data: sub } = supabase.auth.onAuthStateChange((event, newSession) => {
      setSession(newSession ?? null);
      // On sign-out, blow away any cached user-scoped data so the next
      // user can't see the previous one's chats while react-query
      // figures out it should refetch.
      if (event === 'SIGNED_OUT') {
        queryClient.clear();
      }
      // On sign-in, the dialog (if open) has served its purpose.
      if (event === 'SIGNED_IN') {
        setLoginDialogOpen(false);
      }
    });

    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, [queryClient]);

  const signInPassword = useCallback(async ({ email, password }) => {
    setError(null);
    const { error: err } = await supabase.auth.signInWithPassword({ email, password });
    if (err) { setError(err.message); throw err; }
  }, []);

  const signUpPassword = useCallback(async ({ email, password }) => {
    setError(null);
    const { error: err } = await supabase.auth.signUp({ email, password });
    if (err) { setError(err.message); throw err; }
  }, []);

  const signOut = useCallback(async () => {
    setError(null);
    const { error: err } = await supabase.auth.signOut();
    if (err) { setError(err.message); throw err; }
  }, []);

  const openLoginDialog = useCallback((mode = 'signin') => {
    setLoginDialogMode(mode === 'signup' ? 'signup' : 'signin');
    setError(null);
    setLoginDialogOpen(true);
  }, []);

  const closeLoginDialog = useCallback(() => {
    setLoginDialogOpen(false);
  }, []);

  const value = useMemo(() => ({
    session,
    user: session?.user ?? null,
    loading,
    error,
    clearError: () => setError(null),
    signInPassword,
    signUpPassword,
    signOut,
    loginDialogOpen,
    loginDialogMode,
    openLoginDialog,
    closeLoginDialog,
  }), [session, loading, error, signInPassword, signUpPassword, signOut, loginDialogOpen, loginDialogMode, openLoginDialog, closeLoginDialog]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
