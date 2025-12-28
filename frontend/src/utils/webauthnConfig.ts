/**
 * WebAuthn Configuration Utilities
 * Handles domain-specific WebAuthn RP ID configuration
 */

export function getWebAuthnRPID(): string {
  const hostname = window.location.hostname;
  
  // For CloudFront domains, we need to use the actual domain, not a mapped one
  // WebAuthn requires the RP ID to exactly match the domain the user is on
  return hostname;
}

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