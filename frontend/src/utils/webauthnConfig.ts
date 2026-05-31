/**
 * WebAuthn Configuration Utilities
 * 
 * NOTE: Passkey registration and authentication are now handled by Cognito's
 * native WebAuthn support. The RP ID is configured server-side on the Cognito
 * User Pool (h-dcn.nl) and does not need client-side configuration.
 * 
 * These utility functions are kept for UI display purposes only.
 */

export function isTestEnvironment(): boolean {
  const hostname = window.location.hostname;
  return hostname.includes('testportal') || hostname.includes('cloudfront.net') || hostname === 'localhost';
}

export function getEnvironmentName(): string {
  const hostname = window.location.hostname;
  
  if (hostname === 'portal.h-dcn.nl') return 'production';
  if (hostname.includes('testportal')) return 'test';
  if (hostname.includes('cloudfront.net')) return 'test';
  if (hostname === 'localhost') return 'development';
  
  return 'unknown';
}
