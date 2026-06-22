/**
 * Version check (optimistic locking) utility — pure functions for
 * determining whether a save request should succeed or be rejected
 * based on the order's version field.
 *
 * The version field acts as an optimistic lock: each successful save
 * increments the version. A save request must specify the current version
 * to succeed — any mismatch indicates a concurrent modification.
 *
 * Validates: Requirements 5.5, 5.6, 8.3
 */

export interface VersionCheckInput {
  /** Current order version stored on the server */
  currentVersion: number;
  /** Version specified in the save request */
  requestVersion: number;
}

export interface VersionCheckResult {
  /** Whether the save should be accepted */
  accepted: boolean;
  /** The new version after a successful save (currentVersion + 1) */
  newVersion: number | null;
  /** Error type if rejected */
  error: 'VERSION_CONFLICT' | null;
}

/**
 * Check whether a save request should succeed based on optimistic locking.
 *
 * Rules:
 * - If requestVersion === currentVersion: accept, new version = currentVersion + 1
 * - If requestVersion !== currentVersion: reject with VERSION_CONFLICT
 *
 * This is a pure function that mirrors the backend's conditional update logic.
 */
export function checkVersion(input: VersionCheckInput): VersionCheckResult {
  const { currentVersion, requestVersion } = input;

  if (requestVersion === currentVersion) {
    return {
      accepted: true,
      newVersion: currentVersion + 1,
      error: null,
    };
  }

  return {
    accepted: false,
    newVersion: null,
    error: 'VERSION_CONFLICT',
  };
}

/**
 * Simulate a sequence of save operations against a versioned order.
 * Useful for testing that sequential saves with correct versions succeed
 * while concurrent saves with stale versions fail.
 *
 * @param initialVersion - The starting version of the order
 * @param requestVersions - Array of versions specified in successive save requests
 * @returns Array of results for each save attempt
 */
export function simulateSaveSequence(
  initialVersion: number,
  requestVersions: number[]
): VersionCheckResult[] {
  const results: VersionCheckResult[] = [];
  let currentVersion = initialVersion;

  for (const requestVersion of requestVersions) {
    const result = checkVersion({ currentVersion, requestVersion });
    results.push(result);

    // Only advance the version if the save was accepted
    if (result.accepted && result.newVersion !== null) {
      currentVersion = result.newVersion;
    }
  }

  return results;
}
