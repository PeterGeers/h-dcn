/**
 * Membership Type Mapping Utility
 * 
 * Provides consistent mapping between membership type IDs/values and display names
 * to ensure consistent display across all components.
 */

export interface MembershipType {
  id: string;
  value: string;
}

// Default membership types (fallback if API fails)
export const DEFAULT_MEMBERSHIP_TYPES: MembershipType[] = [
  { id: '1', value: 'Gewoon lid' },
  { id: '2', value: 'Gezins lid' },
  { id: '3', value: 'Gezins donateur zonder motor' },
  { id: '4', value: 'Donateur zonder motor' }
];

// Mapping for various possible stored values to display names
const MEMBERSHIP_TYPE_MAPPINGS: Record<string, string> = {
  // ID mappings
  '1': 'Gewoon lid',
  '2': 'Gezins lid',
  '3': 'Gezins donateur zonder motor',
  '4': 'Donateur zonder motor',
  
  // Full name mappings (already correct)
  'Gewoon lid': 'Gewoon lid',
  'Gezins lid': 'Gezins lid',
  'Gezinslid': 'Gezins lid', // Handle variations
  'Gezins donateur zonder motor': 'Gezins donateur zonder motor',
  'Donateur zonder motor': 'Donateur zonder motor',
  
  // Partial/legacy mappings (if any exist)
  'gewoon': 'Gewoon lid',
  'gezin': 'Gezins lid',
  'donateur': 'Donateur zonder motor',
  'gezinsdonateur': 'Gezins donateur zonder motor',
  
  // Handle numeric strings that might be stored
  'lid1': 'Gewoon lid',
  'lid2': 'Gezins lid',
  'lid3': 'Gezins donateur zonder motor',
  'lid4': 'Donateur zonder motor'
};

/**
 * Maps a membership type value to its proper display name
 * 
 * @param value - The raw membership type value from the database
 * @returns The proper display name for the membership type
 */
export function getMembershipTypeDisplayName(value: string | null | undefined): string {
  if (!value) {
    return 'Onbekend';
  }

  // Clean the input value
  const cleanValue = value.toString().trim();
  
  // Try direct mapping first
  if (MEMBERSHIP_TYPE_MAPPINGS[cleanValue]) {
    return MEMBERSHIP_TYPE_MAPPINGS[cleanValue];
  }
  
  // Try case-insensitive mapping
  const lowerValue = cleanValue.toLowerCase();
  for (const [key, displayName] of Object.entries(MEMBERSHIP_TYPE_MAPPINGS)) {
    if (key.toLowerCase() === lowerValue) {
      return displayName;
    }
  }
  
  // If it's a number, try to map it
  if (/^\d+$/.test(cleanValue)) {
    const mappedValue = MEMBERSHIP_TYPE_MAPPINGS[cleanValue];
    if (mappedValue) {
      return mappedValue;
    }
  }
  
  // If it looks like a valid display name already, return it
  if (cleanValue.includes('lid') || cleanValue.includes('donateur')) {
    return cleanValue;
  }
  
  // Last resort: return the original value with a warning prefix
  console.warn(`Unknown membership type value: "${cleanValue}"`);
  return `${cleanValue} (onbekend type)`;
}

/**
 * Gets the membership type ID from a display name
 * 
 * @param displayName - The display name of the membership type
 * @returns The ID of the membership type, or null if not found
 */
export function getMembershipTypeId(displayName: string): string | null {
  for (const [id, name] of Object.entries(MEMBERSHIP_TYPE_MAPPINGS)) {
    if (name === displayName) {
      // Return the first numeric ID found
      if (/^\d+$/.test(id)) {
        return id;
      }
    }
  }
  return null;
}

/**
 * Validates if a membership type value is valid
 * 
 * @param value - The membership type value to validate
 * @returns True if the value is valid, false otherwise
 */
export function isValidMembershipType(value: string): boolean {
  if (!value) return false;
  
  const cleanValue = value.toString().trim();
  return Object.keys(MEMBERSHIP_TYPE_MAPPINGS).some(
    key => key.toLowerCase() === cleanValue.toLowerCase()
  );
}