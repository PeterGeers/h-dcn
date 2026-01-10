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

// H-DCN Complete Organizational Structure - Updated for New Permission + Region Structure
export type HDCNGroup =
  // Basic member role
  | "hdcnLeden"

  // Permission-Based Roles (New System - No more _All roles)
  // Member Management Roles
  | "Members_CRUD"             // Permission to create, read, update, delete member data
  | "Members_Read"             // Permission to read member data
  | "Members_Status_Approve"   // Permission to approve member status changes
  | "Members_Export"           // Export member data permissions

  // Event Management Roles
  | "Events_Read"              // Read event data permissions
  | "Events_CRUD"              // Permission to create, read, update, delete event data
  | "Events_Export"            // Export event data permissions

  // Product Management Roles
  | "Products_Read"            // Permission to read product data
  | "Products_CRUD"            // Permission to create, read, update, delete product data
  | "Products_Export"          // Export product data permissions

  // Communication Roles
  | "Communication_Read"       // Read communication data permissions
  | "Communication_CRUD"       // Full communication management permissions
  | "Communication_Export"     // Export communication data permissions

  // System Administration Roles
  | "System_User_Management"   // System user management permissions
  | "System_Logs_Read"         // Permission to read system logs and audit trails

  // Regional Roles (New System - Permission + Region Structure)
  | "Regio_All"                // Access to all regions (only _All role that still exists)
  | "Regio_Utrecht"            // Access to Utrecht region only
  | "Regio_Limburg"            // Access to Limburg region only
  | "Regio_Groningen/Drenthe"  // Access to Groningen/Drenthe region only
  | "Regio_Zuid-Holland"       // Access to Zuid-Holland region only
  | "Regio_Oost"               // Access to Oost region only
  | "Regio_Brabant/Zeeland"    // Access to Brabant/Zeeland region only
  | "Regio_Friesland"          // Access to Friesland region only
  | "Regio_Duitsland"          // Access to Duitsland region only
  | "Regio_Noord-Holland"      // Access to Noord-Holland region only

  // Webshop Management
  | "Webshop_Management"       // Webshop management permissions - full control over webshop products and orders

  // Special Application Role
  | "verzoek_lid";             // Role for new user registration (no permissions except signup)

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

// Utility functions for H-DCN roles - Updated for new permission + region structure
export const HDCNRoleUtils = {
  isPermissionRole: (role: HDCNGroup): boolean => 
    role.includes("_CRUD") || role.includes("_Read") || role.includes("_Export") || role.includes("_Status_Approve"),
  
  isRegionalRole: (role: HDCNGroup): boolean =>
    role.startsWith("Regio_"),
  
  isSystemRole: (role: HDCNGroup): boolean =>
    role.startsWith("System_"),
  
  extractRegionFromRole: (role: HDCNGroup): string | null => {
    if (role === "Regio_All") return "all";
    if (role.startsWith("Regio_")) {
      const regionName = role.replace("Regio_", "").toLowerCase();
      return regionName.replace("/", "_").replace("-", "_");
    }
    return null;
  },
  
  getRoleType: (role: HDCNGroup): "permission" | "regional" | "system" | "member" | "webshop" => {
    if (HDCNRoleUtils.isPermissionRole(role)) return "permission";
    if (HDCNRoleUtils.isRegionalRole(role)) return "regional";
    if (HDCNRoleUtils.isSystemRole(role)) return "system";
    if (role === "Webshop_Management") return "webshop";
    return "member";
  },
  
  canManageMembers: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      role === "Members_CRUD" || 
      role === "System_User_Management"
    ),
  
  canManageEvents: (roles: HDCNGroup[], targetRegion?: string): boolean =>
    roles.some(role => {
      if (role === "Events_CRUD") return true;
      return false;
    }),
  
  canCreateMailingLists: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      role === "Communication_CRUD" ||
      role === "Members_Export" ||
      role === "Events_Export" ||
      role === "Products_Export" ||
      role === "Communication_Export"
    ),
  
  requiresMFA: (roles: HDCNGroup[]): boolean =>
    roles.some(role => 
      role.startsWith("System_") ||
      role === "Members_CRUD" ||
      role === "Webshop_Management"
    )
};