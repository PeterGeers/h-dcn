/**
 * Regional ID Mapping for Cognito Access Control
 * 
 * This mapping is critical for regional access control in Cognito.
 * Cognito groups use region IDs (Regional_Chairman_Region1, hdcnRegio_1_, etc.)
 * and this mapping translates those IDs to region names.
 * 
 * DO NOT CHANGE these mappings without updating Cognito groups!
 */

export const REGION_ID_TO_NAME_MAP: { [key: string]: string } = {
  '1': 'Noord-Holland',
  '2': 'Zuid-Holland', 
  '3': 'Friesland',
  '4': 'Utrecht',
  '5': 'Oost',
  '6': 'Limburg',
  '7': 'Groningen/Drente',
  '8': 'Noord-Brabant/Zeeland',
  '9': 'Duitsland'
};

export const REGION_NAME_TO_ID_MAP: { [key: string]: string } = {
  'Noord-Holland': '1',
  'Zuid-Holland': '2',
  'Friesland': '3',
  'Utrecht': '4',
  'Oost': '5',
  'Limburg': '6',
  'Groningen/Drente': '7',
  'Noord-Brabant/Zeeland': '8',
  'Duitsland': '9'
};

/**
 * Get region name from Cognito region ID
 */
export const getRegionNameFromId = (regionId: string): string | undefined => {
  return REGION_ID_TO_NAME_MAP[regionId];
};

/**
 * Get region ID from region name (for Cognito compatibility)
 */
export const getRegionIdFromName = (regionName: string): string | undefined => {
  return REGION_NAME_TO_ID_MAP[regionName];
};

/**
 * Check if a user has regional access to a specific region
 */
export const hasRegionalAccess = (userRoles: string[], memberRegion: string): boolean => {
  return userRoles.some(role => {
    // Check for regional roles that match the member's region
    if (role.includes('Regional_') && role.includes('Region')) {
      const regionMatch = role.match(/Region(\d+)/);
      if (regionMatch) {
        const roleRegionId = regionMatch[1];
        const roleRegionName = getRegionNameFromId(roleRegionId);
        return memberRegion === roleRegionName || memberRegion === roleRegionId;
      }
    }
    
    // Legacy regional role support
    if (role.startsWith('hdcnRegio_')) {
      const regionMatch = role.match(/hdcnRegio_(\d+)_/);
      if (regionMatch) {
        const roleRegionId = regionMatch[1];
        const roleRegionName = getRegionNameFromId(roleRegionId);
        return memberRegion === roleRegionName || memberRegion === roleRegionId;
      }
    }
    
    return false;
  });
};

/**
 * Get allowed regions for a user based on their roles
 */
export const getAllowedRegions = (userRoles: string[], hasFullAccess: boolean = false): string[] => {
  if (hasFullAccess) return []; // Full access users can select any region
  
  const allowedRegions: string[] = [];
  
  userRoles.forEach(role => {
    if (role.includes('Regional_') && role.includes('Region')) {
      const regionMatch = role.match(/Region(\d+)/);
      if (regionMatch) {
        const regionId = regionMatch[1];
        const regionName = getRegionNameFromId(regionId);
        if (regionName && !allowedRegions.includes(regionName)) {
          allowedRegions.push(regionName);
        }
      }
    }
  });
  
  return allowedRegions;
};