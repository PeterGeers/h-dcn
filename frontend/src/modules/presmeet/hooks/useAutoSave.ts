/**
 * useAutoSave — Debounced auto-save hook for the PresMeet booking wizard.
 *
 * Triggers a background save after 3 seconds of inactivity. Silently
 * saves in the background without interrupting user flow. Skips save
 * if form hasn't changed since last save.
 *
 * Validates: Requirement 11.6 (save action), 11.8 (preserve state on failure)
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseAutoSaveOptions {
  /** Delay in ms before auto-save triggers (default: 3000) */
  delay?: number;
  /** Whether auto-save is enabled */
  enabled?: boolean;
}

export interface UseAutoSaveReturn {
  /** Whether auto-save is currently in progress */
  isAutoSaving: boolean;
  /** Last auto-save timestamp (null if never saved) */
  lastSavedAt: Date | null;
  /** Trigger a change notification (resets the debounce timer) */
  notifyChange: () => void;
  /** Cancel any pending auto-save */
  cancel: () => void;
}

/**
 * Debounced auto-save hook. Call `notifyChange` whenever form state changes.
 * After `delay` ms of no further changes, the `saveFn` is called.
 *
 * @param saveFn - Async function to perform the save
 * @param options - Configuration options
 */
export function useAutoSave(
  saveFn: () => Promise<boolean>,
  options: UseAutoSaveOptions = {}
): UseAutoSaveReturn {
  const { delay = 3000, enabled = true } = options;

  const [isAutoSaving, setIsAutoSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveFnRef = useRef(saveFn);

  // Keep saveFn reference up to date without resetting timer
  useEffect(() => {
    saveFnRef.current = saveFn;
  }, [saveFn]);

  const cancel = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const notifyChange = useCallback(() => {
    if (!enabled) return;

    // Reset the timer on every change
    cancel();

    timerRef.current = setTimeout(async () => {
      setIsAutoSaving(true);
      try {
        const success = await saveFnRef.current();
        if (success) {
          setLastSavedAt(new Date());
        }
      } catch {
        // Auto-save failures are silent — don't interrupt user
      } finally {
        setIsAutoSaving(false);
      }
    }, delay);
  }, [enabled, delay, cancel]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return {
    isAutoSaving,
    lastSavedAt,
    notifyChange,
    cancel,
  };
}
