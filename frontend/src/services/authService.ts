import { fetchAuthSession } from 'aws-amplify/auth';
import { HDCNGroup } from '../types/user';

/**
 * JWT Token utilities for Cognito authentication
 */

export interface JWTPayload {
  'cognito:groups'?: HDCNGroup[];
  username?: string;
  email?: string;
  sub?: string;
  aud?: string;
  iss?: string;
  exp?: number;
  iat?: number;
}

export interface AuthTokens {
  idToken?: string;
  accessToken?: string;
  refreshToken?: string;
}

/**
 * Extracts JWT payload from a token string
 * @param token - JWT token string
 * @returns Decoded JWT payload or null if invalid
 */
export function decodeJWTPayload(token: string): JWTPayload | null {
  try {
    // JWT tokens have 3 parts separated by dots: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      console.error('Invalid JWT token format');
      return null;
    }

    // Decode the payload (second part)
    const payload = parts[1];
    
    // Add padding if needed for base64 decoding
    const paddedPayload = payload + '='.repeat((4 - payload.length % 4) % 4);
    
    // Decode base64 and parse JSON
    const decodedPayload = JSON.parse(atob(paddedPayload));
    
    return decodedPayload as JWTPayload;
  } catch (error) {
    console.error('Failed to decode JWT payload:', error);
    return null;
  }
}

/**
 * Gets current authentication tokens from Amplify session
 * @returns Promise with current auth tokens or null if not authenticated
 */
export async function getCurrentAuthTokens(): Promise<AuthTokens | null> {
  try {
    const session = await fetchAuthSession();
    
    if (!session.tokens) {
      console.log('No tokens available in session');
      return null;
    }

    return {
      idToken: session.tokens.idToken?.toString(),
      accessToken: session.tokens.accessToken?.toString(),
      // Note: refreshToken may not be available in all Amplify v6 configurations
      refreshToken: (session.tokens as any).refreshToken?.toString()
    };
  } catch (error) {
    console.error('Failed to get auth tokens:', error);
    return null;
  }
}

/**
 * Extracts cognito:groups from current user's JWT tokens
 * @returns Promise with array of user roles/groups or empty array if none found
 */
export async function getCurrentUserRoles(): Promise<HDCNGroup[]> {
  try {
    const tokens = await getCurrentAuthTokens();
    
    if (!tokens?.accessToken) {
      console.log('No access token available');
      return [];
    }

    const payload = decodeJWTPayload(tokens.accessToken);
    
    if (!payload) {
      console.error('Failed to decode access token payload');
      return [];
    }

    const cognitoGroups = payload['cognito:groups'] || [];
    console.log('Extracted cognito:groups from JWT:', cognitoGroups);
    
    return cognitoGroups;
  } catch (error) {
    console.error('Failed to extract user roles from JWT:', error);
    return [];
  }
}

/**
 * Validates that JWT token contains expected cognito:groups claim
 * @param token - JWT token string to validate
 * @returns boolean indicating if token contains valid cognito:groups claim
 */
export function validateCognitoGroupsClaim(token: string): boolean {
  const payload = decodeJWTPayload(token);
  
  if (!payload) {
    console.error('Invalid JWT token - cannot decode payload');
    return false;
  }

  // Check if cognito:groups claim exists (can be empty array)
  if (!payload.hasOwnProperty('cognito:groups')) {
    console.error('JWT token missing cognito:groups claim');
    return false;
  }

  // Validate that cognito:groups is an array
  if (!Array.isArray(payload['cognito:groups'])) {
    console.error('cognito:groups claim is not an array');
    return false;
  }

  console.log('JWT token contains valid cognito:groups claim:', payload['cognito:groups']);
  return true;
}

/**
 * Gets user information from JWT tokens including roles
 * @returns Promise with user info extracted from JWT tokens
 */
export async function getCurrentUserInfo(): Promise<{
  username?: string;
  email?: string;
  roles: HDCNGroup[];
  sub?: string;
} | null> {
  try {
    const tokens = await getCurrentAuthTokens();
    
    if (!tokens?.accessToken) {
      return null;
    }

    const payload = decodeJWTPayload(tokens.accessToken);
    
    if (!payload) {
      return null;
    }

    return {
      username: payload.username,
      email: payload.email,
      roles: payload['cognito:groups'] || [],
      sub: payload.sub
    };
  } catch (error) {
    console.error('Failed to get current user info:', error);
    return null;
  }
}