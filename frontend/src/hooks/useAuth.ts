/**
 * useAuth hook — re-exports from AuthProvider context.
 *
 * This module provides a convenience import path for the useAuth hook.
 * The canonical implementation lives in src/context/AuthProvider.tsx.
 *
 * Requirements: R4.1, R4.2
 * - Auth state comes from fetchAuthSession() — not from localStorage.
 * - User groups come from the access token payload — not from manual JWT decoding or hardcoded fallbacks.
 */

export { useAuth, AuthProvider } from '../context/AuthProvider';
export type { AuthUser, AuthContextType } from '../context/AuthProvider';
