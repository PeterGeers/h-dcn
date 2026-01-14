/**
 * Status Translation Utility
 * Maps Dutch frontend status values to English backend values
 */

// Map Dutch status values (frontend) to English values (backend)
const STATUS_NL_TO_EN: Record<string, string> = {
  'Actief': 'active',
  'Opgezegd': 'cancelled',
  'wachtRegio': 'pending',
  'Aangemeld': 'new_applicant',
  'Geschorst': 'suspended',
  'HdcnAccount': 'active',
  'Club': 'active',
  'Sponsor': 'active',
  'Overig': 'active'
};

// Map English status values (backend) to Dutch values (frontend)
const STATUS_EN_TO_NL: Record<string, string> = {
  'active': 'Actief',
  'cancelled': 'Opgezegd',
  'pending': 'wachtRegio',
  'new_applicant': 'Aangemeld',
  'suspended': 'Geschorst',
  'inactive': 'Opgezegd',
  'approved': 'Actief',
  'rejected': 'Opgezegd',
  'expired': 'Opgezegd'
};

/**
 * Convert Dutch status to English for backend
 */
export function statusToBackend(dutchStatus: string | undefined | null): string | undefined {
  if (!dutchStatus) return undefined;
  return STATUS_NL_TO_EN[dutchStatus] || dutchStatus.toLowerCase();
}

/**
 * Convert English status from backend to Dutch for frontend
 */
export function statusFromBackend(englishStatus: string | undefined | null): string | undefined {
  if (!englishStatus) return undefined;
  return STATUS_EN_TO_NL[englishStatus.toLowerCase()] || englishStatus;
}

/**
 * Transform member data before sending to backend
 * Converts Dutch status values to English
 */
export function transformMemberForBackend(member: any): any {
  if (!member) return member;
  
  const transformed = { ...member };
  
  if (transformed.status) {
    transformed.status = statusToBackend(transformed.status);
  }
  
  return transformed;
}

/**
 * Transform member data from backend for frontend display
 * Converts English status values to Dutch
 */
export function transformMemberFromBackend(member: any): any {
  if (!member) return member;
  
  const transformed = { ...member };
  
  if (transformed.status) {
    transformed.status = statusFromBackend(transformed.status);
  }
  
  return transformed;
}
