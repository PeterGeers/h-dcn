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
  // Algemeen Bestuur (General Board)
  | "hdcnVoorzitter"           // Chairman
  | "hdcnSecretaris"           // Secretary (= Landelijke Secretaris)
  | "hdcnPenningmeester"       // Treasurer
  | "hdcnViceVoorzitter"       // Vice Chairman
  | "hdcnLedenadministratie"   // Member Administration

  // Ondersteunende Rollen (Supporting Roles)
  | "hdcnWebmaster"            // Can have multiple roles
  | "hdcnToercomisaris"        // Tour Commissioner
  | "hdcnClubblad"             // Club Magazine
  | "hdcnWebshop"              // Webshop Management

  // Regionale Rollen (Regional Roles) - 9 regions
  // Regio 1
  | "hdcnRegio_1_Voorzitter"
  | "hdcnRegio_1_Penningmeester"
  | "hdcnRegio_1_Secretaris"
  | "hdcnRegio_1_Vrijwilliger"
  
  // Regio 2
  | "hdcnRegio_2_Voorzitter"
  | "hdcnRegio_2_Penningmeester"
  | "hdcnRegio_2_Secretaris"
  | "hdcnRegio_2_Vrijwilliger"
  
  // Regio 3
  | "hdcnRegio_3_Voorzitter"
  | "hdcnRegio_3_Penningmeester"
  | "hdcnRegio_3_Secretaris"
  | "hdcnRegio_3_Vrijwilliger"
  
  // Regio 4
  | "hdcnRegio_4_Voorzitter"
  | "hdcnRegio_4_Penningmeester"
  | "hdcnRegio_4_Secretaris"
  | "hdcnRegio_4_Vrijwilliger"
  
  // Regio 5
  | "hdcnRegio_5_Voorzitter"
  | "hdcnRegio_5_Penningmeester"
  | "hdcnRegio_5_Secretaris"
  | "hdcnRegio_5_Vrijwilliger"
  
  // Regio 6
  | "hdcnRegio_6_Voorzitter"
  | "hdcnRegio_6_Penningmeester"
  | "hdcnRegio_6_Secretaris"
  | "hdcnRegio_6_Vrijwilliger"
  
  // Regio 7
  | "hdcnRegio_7_Voorzitter"
  | "hdcnRegio_7_Penningmeester"
  | "hdcnRegio_7_Secretaris"
  | "hdcnRegio_7_Vrijwilliger"
  
  // Regio 8
  | "hdcnRegio_8_Voorzitter"
  | "hdcnRegio_8_Penningmeester"
  | "hdcnRegio_8_Secretaris"
  | "hdcnRegio_8_Vrijwilliger"
  
  // Regio 9
  | "hdcnRegio_9_Voorzitter"
  | "hdcnRegio_9_Penningmeester"
  | "hdcnRegio_9_Secretaris"
  | "hdcnRegio_9_Vrijwilliger"

  // Basis Leden (Basic Members)
  | "hdcnLeden";

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