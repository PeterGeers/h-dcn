// User type definitions for H-DCN Dashboard

export interface User {
  id: string;
  username: string;
  email: string;
  groups: HDCNGroup[];
  attributes: Record<string, string>;
}

export interface CognitoUser {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: HDCNGroup[];
        username: string;
        email: string;
      };
    };
  };
}

// H-DCN Complete Organizational Structure
export type HDCNGroup =
  // Basis Leden (Basic Members)
  | "hdcnLeden"

  // Permission-Based Roles (New System)
  // Member Management Roles
  | "Members_CRUD_All"         // Full member administration
  | "Members_Read_All"         // Read all member data
  | "Members_Status_Approve"   // Approve member status changes
  | "Members_Export_All"       // Export member data

  // Event Management Roles
  | "Events_Read_All"          // Read all events
  | "Events_CRUD_All"          // Full event management
  | "Events_Export_All"        // Export event data

  // Product Management Roles
  | "Products_Read_All"        // Read all products
  | "Products_CRUD_All"        // Full product management
  | "Products_Export_All"      // Export product data

  // Communication Roles
  | "Communication_Read_All"   // Read all communication
  | "Communication_Export_All" // Export communication data
  | "Communication_CRUD_All"   // Full communication management

  // System Administration Roles
  | "System_User_Management"   // User and role management
  | "System_CRUD_All"          // Full system administration
  | "System_Logs_Read"         // Read system logs and audit

  // Organizational Roles (New System)
  | "National_Chairman"        // National Chairman
  | "National_Secretary"       // National Secretary
  | "National_Treasurer"       // National Treasurer
  | "Webmaster"               // Webmaster
  | "Tour_Commissioner"        // Tour Commissioner
  | "Club_Magazine_Editorial"  // Club Magazine Editorial
  | "Webshop_Management"      // Webshop Management

  // Regional Roles (New System - Examples)
  | "Regional_Chairman"        // Regional Chairman (generic)
  | "Regional_Secretary"       // Regional Secretary (generic)
  | "Regional_Treasurer"       // Regional Treasurer (generic)
  | "Regional_Volunteer"       // Regional Volunteer (generic)
  | "Regional_Chairman_Region1"    // Region-specific roles
  | "Regional_Secretary_Region1"
  | "Regional_Treasurer_Region1"
  | "Regional_Volunteer_Region1"
  | "Regional_Chairman_Region2"
  | "Regional_Secretary_Region2"
  | "Regional_Treasurer_Region2"
  | "Regional_Volunteer_Region2"
  | "Regional_Chairman_Region3"
  | "Regional_Secretary_Region3"
  | "Regional_Treasurer_Region3"
  | "Regional_Volunteer_Region3"
  | "Regional_Chairman_Region4"
  | "Regional_Secretary_Region4"
  | "Regional_Treasurer_Region4"
  | "Regional_Volunteer_Region4"

  // Legacy Roles (Old System - for backward compatibility)
  | "hdcnAdmins"              // Legacy admin role
  | "hdcnVoorzitter"          // Chairman
  | "hdcnSecretaris"          // Secretary (= Landelijke Secretaris)
  | "hdcnPenningmeester"      // Treasurer
  | "hdcnViceVoorzitter"      // Vice Chairman
  | "hdcnLedenadministratie"  // Member Administration
  | "hdcnWebmaster"           // Can have multiple roles
  | "hdcnToercomisaris"       // Tour Commissioner
  | "hdcnClubblad"            // Club Magazine
  | "hdcnWebshop"             // Webshop Management

  // Legacy Regional Roles (Old System)
  | "hdcnRegio_1_Voorzitter"
  | "hdcnRegio_1_Penningmeester"
  | "hdcnRegio_1_Secretaris"
  | "hdcnRegio_1_Vrijwilliger"
  | "hdcnRegio_2_Voorzitter"
  | "hdcnRegio_2_Penningmeester"
  | "hdcnRegio_2_Secretaris"
  | "hdcnRegio_2_Vrijwilliger"
  | "hdcnRegio_3_Voorzitter"
  | "hdcnRegio_3_Penningmeester"
  | "hdcnRegio_3_Secretaris"
  | "hdcnRegio_3_Vrijwilliger"
  | "hdcnRegio_4_Voorzitter"
  | "hdcnRegio_4_Penningmeester"
  | "hdcnRegio_4_Secretaris"
  | "hdcnRegio_4_Vrijwilliger"
  | "hdcnRegio_5_Voorzitter"
  | "hdcnRegio_5_Penningmeester"
  | "hdcnRegio_5_Secretaris"
  | "hdcnRegio_5_Vrijwilliger"
  | "hdcnRegio_6_Voorzitter"
  | "hdcnRegio_6_Penningmeester"
  | "hdcnRegio_6_Secretaris"
  | "hdcnRegio_6_Vrijwilliger"
  | "hdcnRegio_7_Voorzitter"
  | "hdcnRegio_7_Penningmeester"
  | "hdcnRegio_7_Secretaris"
  | "hdcnRegio_7_Vrijwilliger"
  | "hdcnRegio_8_Voorzitter"
  | "hdcnRegio_8_Penningmeester"
  | "hdcnRegio_8_Secretaris"
  | "hdcnRegio_8_Vrijwilliger"
  | "hdcnRegio_9_Voorzitter"
  | "hdcnRegio_9_Penningmeester"
  | "hdcnRegio_9_Secretaris"
  | "hdcnRegio_9_Vrijwilliger";

// Legacy type for backward compatibility
export type UserRole = HDCNGroup;

// H-DCN Permission Levels
export interface HDCNPermissions {
  memberData: "none" | "own" | "region" | "basic_all" | "full_all";
  memberExport: boolean;
  events: "none" | "view" | "own_region" | "all_regions";
  eventManagement: "none" | "own_region" | "all_regions";
  webshop: "none" | "customer" | "admin";
  clubblad: "none" | "mailing_lists" | "full_admin";
  mailingListCreation: boolean;
  systemAdmin: boolean;
  cognitoAdmin: boolean;
  ledenadministratie: boolean;
}

// H-DCN Member with organizational context
export interface HDCNMember extends User {
  region: string;
  roles: HDCNGroup[];
  permissions: HDCNPermissions;
  membershipStatus: "new_applicant" | "active" | "inactive" | "suspended" | "ended" | "sponsor";
  membershipType: "individual" | "family" | "corporate";
}

// Utility functions for H-DCN roles
export const HDCNRoleUtils = {
  isGeneralBoard: (role: HDCNGroup): boolean => 
    ["hdcnVoorzitter", "hdcnSecretaris", "hdcnViceVoorzitter", "hdcnPenningmeester", "hdcnLedenadministratie"].includes(role),
  
  isSupportingRole: (role: HDCNGroup): boolean =>
    ["hdcnWebmaster", "hdcnToercomisaris", "hdcnClubblad", "hdcnWebshop"].includes(role),
  
  isRegionalRole: (role: HDCNGroup): boolean =>
    role.startsWith("hdcnRegio_"),
  
  extractRegionFromRole: (role: HDCNGroup): string | null => {
    const match = role.match(/hdcnRegio_(\d+)_/);
    return match ? `regio_${match[1]}` : null;
  },
  
  getRoleType: (role: HDCNGroup): "general" | "supporting" | "regional" | "member" => {
    if (HDCNRoleUtils.isGeneralBoard(role)) return "general";
    if (HDCNRoleUtils.isSupportingRole(role)) return "supporting";
    if (HDCNRoleUtils.isRegionalRole(role)) return "regional";
    return "member";
  },
  
  canManageMembers: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      HDCNRoleUtils.isGeneralBoard(role) || 
      role === "hdcnWebmaster" || 
      role.includes("_Secretaris")
    ),
  
  canManageEvents: (roles: HDCNGroup[], targetRegion?: string): boolean =>
    roles.some(role => {
      if (["hdcnSecretaris", "hdcnToercomisaris"].includes(role)) return true;
      if (role.includes("_Secretaris") && targetRegion) {
        const roleRegion = HDCNRoleUtils.extractRegionFromRole(role);
        return roleRegion === targetRegion;
      }
      return false;
    }),
  
  canCreateMailingLists: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      HDCNRoleUtils.isGeneralBoard(role) || 
      ["hdcnWebmaster", "hdcnToercomisaris", "hdcnClubblad"].includes(role) ||
      role.includes("_Secretaris") || 
      role.includes("_Voorzitter") || 
      role.includes("_Penningmeester")
    ),
  
  requiresMFA: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      HDCNRoleUtils.isGeneralBoard(role) || 
      role === "hdcnWebmaster"
    )
};