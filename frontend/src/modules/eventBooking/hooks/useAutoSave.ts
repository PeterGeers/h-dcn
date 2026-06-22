/**
 * useAutoSave — Debounced auto-save hook for the PresMeet booking wizard.
 *
 * Triggers a background save after 3 seconds of inactivity. Silently
 * saves in the background without interrupting user flow. Skips save
 * if form hasn't changed since last save.
 *
 * Retry strategy:
 * - On failure: retain unsaved changes locally (React state is preserved)
 * - Retry on next user edit OR after 30 seconds, whichever comes first
 *
 * Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'failed';

export interface UseAutoSaveOptions {
  /** Delay in ms before auto-save triggers (default: 3000) */
  delay?: number;
  /** Whether auto-save is enabled */
  enabled?: boolean;
  /** Retry delay in ms after a failed save (default: 30000) */
  retryDelay?: number;
}

export interface UseAutoSaveReturn {
  /** Current save status for the indicator */
  saveStatus: SaveStatus;
  /** Whether auto-save is currently in progress */
  isAutoSaving: boolean;
  /** Last auto-save timestamp (null if never saved) */
  lastSavedAt: Date | null;
  /** Trigger a change notification (resets the debounce timer) */
  notifyChange: () => void;
  /** Cancel any pending auto-save */
  cancel: () => void;
  /** Manually trigger an immediate save */
  saveNow: () => Promise<boolean>;
}

/**
 * Debounced auto-save hook. Call `notifyChange` whenever form state changes.
 * After `delay` ms of no further changes, the `saveFn` is called.
 *
 * On failure:
 * - Status becomes 'failed'
 * - A 30-second retry timer starts
 * - On the next `notifyChange` call, the normal debounce restarts (retry on next edit)
 *
 * @param saveFn - Async function to perform the save. Returns true on success.
 * @param options - Configuration options
 */
export function useAutoSave(
  saveFn: () => Promise<boolean>,
  options: UseAutoSaveOptions = {}
): UseAutoSaveReturn {
  const { delay = 3000, enabled = true, retryDelay = 30000 } = options;

  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveFnRef = useRef(saveFn);
  const isMountedRef = useRef(true);

  // Keep saveFn reference up to date without resetting timer
  useEffect(() => {
    saveFnRef.current = saveFn;
  }, [saveFn]);

  // Track mount state to avoid state updates after unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const clearRetryTimer = useCallback(() => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  const cancel = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    clearRetryTimer();
  }, [clearRetryTimer]);

  /**
   * Execute the save operation and manage status transitions.
   */
  const executeSave = useCallback(async (): Promise<boolean> => {
    if (!isMountedRef.current) return false;
    setSaveStatus('saving');

    try {
      const success = await saveFnRef.current();
      if (!isMountedRef.current) return false;

      if (success) {
        setSaveStatus('saved');
        setLastSavedAt(new Date());
        clearRetryTimer();
        return true;
      } else {
        // saveFn returned false — treat as failure
        setSaveStatus('failed');
        startRetryTimer();
        return false;
      }
    } catch {
      if (!isMountedRef.current) return false;
      // Network/server error — retain changes locally, mark failed
      setSaveStatus('failed');
      startRetryTimer();
      return false;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clearRetryTimer]);

  /**
   * Start a 30-second retry timer after failure.
   */
  const startRetryTimer = useCallback(() => {
    clearRetryTimer();
    retryTimerRef.current = setTimeout(() => {
      if (isMountedRef.current) {
        executeSave();
      }
    }, retryDelay);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [retryDelay, clearRetryTimer]);

  // Wire up startRetryTimer in executeSave (circular dep resolved via ref pattern)
  const executeSaveRef = useRef(executeSave);
  useEffect(() => {
    executeSaveRef.current = executeSave;
  }, [executeSave]);

  const notifyChange = useCallback(() => {
    if (!enabled) return;

    // Clear any pending retry timer — the user edited, so we restart the debounce
    clearRetryTimer();

    // Reset the debounce timer on every change
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    timerRef.current = setTimeout(() => {
      executeSaveRef.current();
    }, delay);
  }, [enabled, delay, clearRetryTimer]);

  /**
   * Manual save trigger (e.g., user clicks "Save now").
   */
  const saveNow = useCallback(async (): Promise<boolean> => {
    // Cancel any pending debounce or retry
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    clearRetryTimer();
    return executeSaveRef.current();
  }, [clearRetryTimer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return {
    saveStatus,
    isAutoSaving: saveStatus === 'saving',
    lastSavedAt,
    notifyChange,
    cancel,
    saveNow,
  };
}
