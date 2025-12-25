# H-DCN Cognito Groups Reference

## Overview

This document provides a comprehensive reference for all AWS Cognito User Pool Groups (roles) created for the H-DCN authentication system. These groups are defined in the SAM template (`backend/template.yaml`) and deployed as part of the Infrastructure as Code (IaC) approach.

**User Pool:** H-DCN-Authentication-Pool  
**User Pool ID:** Referenced via `!Ref HDCNCognitoUserPool` in CloudFormation  
**Deployment:** Managed through AWS SAM (`sam build && sam deploy`)

## Group Hierarchy and Precedence

Groups are ordered by precedence (lower numbers = higher priority):

| Precedence | Group Name               | Category           | Description                                                      |
| ---------- | ------------------------ | ------------------ | ---------------------------------------------------------------- |
| 5          | System_User_Management   | System Admin       | System user management permissions                               |
| 10         | Members_CRUD_All         | Member Management  | Full member management permissions                               |
| 15         | Members_Status_Approve   | Member Management  | Permission to approve member status changes                      |
| 20         | Members_Read_All         | Member Management  | Read access to all member data                                   |
| 25         | Events_CRUD_All          | Event Management   | Full event management permissions                                |
| 30         | Events_Read_All          | Event Management   | Read access to all events                                        |
| 35         | Products_CRUD_All        | Product Management | Full product management permissions                              |
| 40         | Products_Read_All        | Product Management | Read access to all products                                      |
| 45         | Communication_Export_All | Communication      | Permission to export communication data and create mailing lists |
| 50         | Communication_Read_All   | Communication      | Read access to all communication data                            |
| 55         | System_Logs_Read         | System Admin       | Permission to read system logs and audit trails                  |
| 100        | hdcnLeden                | Basic Member       | Basic H-DCN member role - access to personal data and webshop    |

## Detailed Group Definitions

### Basic Member Role

#### hdcnLeden

- **CloudFormation Resource:** `HDCNLedenGroup`
- **Group Name:** `hdcnLeden`
- **Precedence:** 100
- **Description:** "Basic H-DCN member role - access to personal data and webshop"
- **Purpose:** Default role for all H-DCN members
- **Permissions:** Update own personal data, view public events, browse product catalog

### Member Management Roles

#### Members_CRUD_All

- **CloudFormation Resource:** `MembersCRUDAllGroup`
- **Group Name:** `Members_CRUD_All`
- **Precedence:** 10
- **Description:** "Full member management permissions - create, read, update, delete all member data"
- **Purpose:** Complete member data management
- **Permissions:** Full CRUD access to all member records, including administrative fields

#### Members_Read_All

- **CloudFormation Resource:** `MembersReadAllGroup`
- **Group Name:** `Members_Read_All`
- **Precedence:** 20
- **Description:** "Read access to all member data"
- **Purpose:** View-only access to member information
- **Permissions:** Read access to all member data across all regions

#### Members_Status_Approve

- **CloudFormation Resource:** `MembersStatusApproveGroup`
- **Group Name:** `Members_Status_Approve`
- **Precedence:** 15
- **Description:** "Permission to approve member status changes"
- **Purpose:** Approve membership status changes
- **Permissions:** Modify member status field, approve new applications

### Event Management Roles

#### Events_CRUD_All

- **CloudFormation Resource:** `EventsCRUDAllGroup`
- **Group Name:** `Events_CRUD_All`
- **Precedence:** 25
- **Description:** "Full event management permissions"
- **Purpose:** Complete event management
- **Permissions:** Create, read, update, delete all events

#### Events_Read_All

- **CloudFormation Resource:** `EventsReadAllGroup`
- **Group Name:** `Events_Read_All`
- **Precedence:** 30
- **Description:** "Read access to all events"
- **Purpose:** View-only access to event information
- **Permissions:** Read access to all events and event data

### Product Management Roles

#### Products_CRUD_All

- **CloudFormation Resource:** `ProductsCRUDAllGroup`
- **Group Name:** `Products_CRUD_All`
- **Precedence:** 35
- **Description:** "Full product management permissions"
- **Purpose:** Complete product and webshop management
- **Permissions:** Create, read, update, delete all products and webshop items

#### Products_Read_All

- **CloudFormation Resource:** `ProductsReadAllGroup`
- **Group Name:** `Products_Read_All`
- **Precedence:** 40
- **Description:** "Read access to all products"
- **Purpose:** View-only access to product information
- **Permissions:** Read access to all products and webshop data

### Communication Roles

#### Communication_Export_All

- **CloudFormation Resource:** `CommunicationExportAllGroup`
- **Group Name:** `Communication_Export_All`
- **Precedence:** 45
- **Description:** "Permission to export communication data and create mailing lists"
- **Purpose:** Data export and mailing list creation
- **Permissions:** Export member data for communications, create mailing lists

#### Communication_Read_All

- **CloudFormation Resource:** `CommunicationReadAllGroup`
- **Group Name:** `Communication_Read_All`
- **Precedence:** 50
- **Description:** "Read access to all communication data"
- **Purpose:** View communication and newsletter data
- **Permissions:** Read access to communication data and member preferences

### System Administration Roles

#### System_User_Management

- **CloudFormation Resource:** `SystemUserManagementGroup`
- **Group Name:** `System_User_Management`
- **Precedence:** 5
- **Description:** "System user management permissions"
- **Purpose:** Manage user accounts and role assignments
- **Permissions:** Manage Cognito users, assign roles, system administration

#### System_Logs_Read

- **CloudFormation Resource:** `SystemLogsReadGroup`
- **Group Name:** `System_Logs_Read`
- **Precedence:** 55
- **Description:** "Permission to read system logs and audit trails"
- **Purpose:** System monitoring and audit access
- **Permissions:** Read system logs, audit trails, monitoring data

## Common Role Combinations

### Member Administration

**Roles:** `Members_CRUD_All`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_User_Management`
**Purpose:** Complete member management with system administration
**Use Case:** Board members responsible for member administration

### National Chairman

**Roles:** `Members_Read_All`, `Members_Status_Approve`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_Logs_Read`
**Purpose:** Oversight and approval authority
**Use Case:** National chairman with approval and monitoring rights

### Webmaster

**Roles:** `Members_Read_All`, `Events_CRUD_All`, `Products_CRUD_All`, `Communication_CRUD_All`, `System_CRUD_All`
**Purpose:** Complete system management
**Use Case:** Technical administrator with full system access

### Regular Members

**Roles:** `hdcnLeden`
**Purpose:** Basic member access
**Use Case:** Standard H-DCN members

## CloudFormation Outputs

The following outputs are available for application configuration:

### HDCNBasicMemberRole

- **Value:** Reference to `HDCNLedenGroup`
- **Export Name:** `${AWS::StackName}-HDCNLedenGroup`
- **Purpose:** Basic member role group reference

### HDCNAdminRoles

- **Value:** Comma-separated list of admin roles
- **Export Name:** `${AWS::StackName}-HDCNAdminRoles`
- **Content:** `Members_CRUD_All`, `System_User_Management`, `Events_CRUD_All`, `Products_CRUD_All`
- **Purpose:** List of administrative role groups

## Usage in Application

### JWT Token Structure

When users authenticate, their JWT tokens contain a `cognito:groups` claim with their assigned group names:

```json
{
  "cognito:groups": ["hdcnLeden", "Members_Read_All"]
}
```

### Role Extraction

Frontend applications can extract roles using:

```typescript
const getUserRoles = (user: CognitoUser): string[] => {
  return user.signInUserSession?.idToken?.payload["cognito:groups"] || [];
};
```

### Permission Calculation

Roles are mapped to permissions using the `ROLE_PERMISSIONS` constant in the application.

## Deployment and Management

### Infrastructure as Code

- **Template:** `backend/template.yaml`
- **Deployment:** `sam build && sam deploy`
- **Version Control:** All changes tracked in Git

### Group Management

- **Creation:** Automatic via SAM deployment
- **Updates:** Modify template and redeploy
- **Deletion:** Remove from template (use caution)

### User Assignment

- **Manual:** AWS Console or CLI
- **Automatic:** Lambda triggers for new users
- **API:** Cognito Admin API endpoints

## Security Considerations

### Precedence Rules

- Lower precedence numbers have higher priority
- System administration roles have highest precedence (5)
- Basic member role has lowest precedence (100)

### Role Inheritance

- Users can have multiple roles
- Permissions are combined (union of all role permissions)
- No role conflicts due to additive permission model

### Audit Trail

- All role assignments are logged
- Changes tracked through CloudFormation
- User actions tied to specific roles

## Maintenance Notes

### Adding New Roles

1. Add new `AWS::Cognito::UserPoolGroup` resource to SAM template
2. Set appropriate precedence and description
3. Deploy via `sam deploy`
4. Update application permission mappings

### Modifying Existing Roles

1. Update group properties in SAM template
2. Deploy changes via `sam deploy`
3. Test role functionality
4. Update documentation

### Removing Roles

1. Ensure no users are assigned to the role
2. Remove from SAM template
3. Deploy changes
4. Update application code to remove references

---

**Last Updated:** December 25, 2024  
**Template Version:** Current production deployment  
**Maintained By:** H-DCN Development Team
