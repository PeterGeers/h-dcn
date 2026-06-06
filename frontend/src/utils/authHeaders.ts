/**
 * Auth Headers utility - provides authenticated request headers using Amplify v6.
 *
 * Uses fetchAuthSession() as the single source of truth for tokens and groups.
 * No localStorage reads or manual JWT decoding.
 *
 * Requirements: R4.3, R6.6
 */

import { fetchAuthSession } from 'aws-amplify/auth';
import i18n from '../i18n';

/**
 * Filters cognito groups to only include valid role structure roles.
 * Ensures only current permission + region role combinations are used.
 */
const filterValidRoles = (groups: string[]): string[] => {
  return groups.filter((role: string) => {
    // Silently skip Cognito identity provider groups (e.g. eu-west-1_fcUkvwjH5_Google)
    if (/^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+_/.test(role)) {
      return false;
    }

    // Allow permission-based roles (current system)
    if (role.includes('_CRUD') || role.includes('_Read') || role.includes('_Export') || role.includes('_Status_Approve')) {
      // Note: Regio_All is the only _All role that still exists
      if (role.endsWith('_All') && role !== 'Regio_All') {
        console.warn(`AuthHeaders: Filtering out invalid role: ${role}`);
        return false;
      }
      return true;
    }

    // Allow regional roles
    if (role.startsWith('Regio_')) {
      return true;
    }

    // Allow system roles
    if (role.startsWith('System_')) {
      return true;
    }

    // Allow specific valid roles
    if (['hdcnLeden', 'Webshop_Management', 'verzoek_lid'].includes(role)) {
      return true;
    }

    // Allow club/presmeet roles
    if (role.startsWith('club_')) {
      return true;
    }

    // Reject any other invalid roles
    console.warn(`AuthHeaders: Filtering out invalid role: ${role}`);
    return false;
  });
};

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();

  if (!token) throw new Error('Not authenticated');

  const userGroups = (session.tokens?.accessToken?.payload?.['cognito:groups'] as string[] | undefined) ?? [];
  const userEmail = (session.tokens?.idToken?.payload?.email as string | undefined) ?? '';

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    'Accept-Language': i18n.language,
  };

  // Add user email from ID token for backend identity resolution
  if (userEmail) {
    headers['X-User-Email'] = userEmail;
  }

  // Add enhanced groups header for backend permission validation
  if (userGroups.length > 0) {
    const validGroups = filterValidRoles(userGroups);
    headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
  }

  return headers;
};

export const getAuthHeadersForGet = async (): Promise<Record<string, string>> => {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();

  if (!token) throw new Error('Not authenticated');

  const userGroups = (session.tokens?.accessToken?.payload?.['cognito:groups'] as string[] | undefined) ?? [];
  const userEmail = (session.tokens?.idToken?.payload?.email as string | undefined) ?? '';

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    'Accept-Language': i18n.language,
  };

  // Add user email from ID token for backend identity resolution
  if (userEmail) {
    headers['X-User-Email'] = userEmail;
  }

  // Add enhanced groups header for backend permission validation
  if (userGroups.length > 0) {
    const validGroups = filterValidRoles(userGroups);
    headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
  }

  return headers;
};
