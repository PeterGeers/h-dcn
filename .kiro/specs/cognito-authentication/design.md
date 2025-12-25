# H-DCN Cognito Authentication - Design Document

## Overview

We are creating a role-based authentication system where:

1. **User accounts** are authenticated via passwordless methods (passkeys with email recovery)
2. **Roles are assigned** to user accounts based on organizational functions and membership status
3. **Permissions are determined** by the roles assigned to the authenticated user account

**Note:** This implementation utilizes AWS Cognito's native passwordless authentication capabilities (available since November 2024) to ensure simplicity, maintainability, and cost-effectiveness.

## Authentication Methods

### Passwordless Authentication

**Primary Method: Passkeys**

- WebAuthn-based authentication using device biometrics (Face ID, fingerprint) or device PIN
- Phishing-resistant and user-friendly
- Supported across mobile and desktop devices

**Fallback Method: Email Recovery**

- Email-based account recovery when passkeys are unavailable
- No passwords required - users receive email verification links
- New passkey setup after email verification

**Enhanced Security for Administrative Roles**

- MFA (additional verification) required for administrative roles when suspicious activity is detected
- Regular members use passkeys only for streamlined experience

## User Account Types

### Regular Member Accounts

- Any email address (personal or organizational)
- Authenticated via passkeys with email recovery fallback
- Assigned roles based on membership status and organizational functions

### Administrative Accounts

- Users with administrative roles (board members, webmaster, member administration)
- Enhanced security with MFA when suspicious activity is detected
- Same passwordless authentication with additional verification layer

## H-DCN Organizational Functions

### General Board (5 functions)

- National Chairman
- National Secretary
- Member Administration
- National Treasurer
- Vice-Chairman

### Supporting Functions (4 functions)

- Webmaster
- Tour Commissioner
- Club Magazine Editorial
- Webshop Management

### Regional Functions (36 functions across 9 regions)

- Regional Chairman (per region)
- Regional Secretary (per region)
- Regional Treasurer (per region)
- Regional Volunteer (per region)

### Basic Members

- Regular Members (hdcnLeden)

## Role-Based Access Control

### User → Roles → Permissions Hierarchy

**Example: User with National Chairman Role**

```
User: jan.jansen@gmail.com
↓
Roles: ["Members_Read_All", "Members_Status_Approve", "Events_Read_All", "Products_Read_All", "Communication_Read_All", "System_Logs_Read"]
↓
Permissions: View all member data + approve status, view all events/products/communication, view system logs
```

**Example: User with Regional Secretary Role**

```
User: marie.pietersen@hotmail.com
↓
Roles: ["Members_Read_Region1", "Members_Export_Region1", "Events_Read_Region1", "Products_Read_All", "Communication_Export_Region1"]
↓
Permissions: View/export Region 1 member data, view Region 1 events, view all products, create Region 1 mailing lists
```

**Example: Regular Member**

```
User: piet.klaassen@ziggo.nl
↓
Roles: ["hdcnLeden"]
↓
Permissions: Update own personal data, view public events, browse product catalog
```

## Permission Matrix

| Role Assignment             | Member Data                   | Events                    | Products            | Communication     | System Admin    |
| --------------------------- | ----------------------------- | ------------------------- | ------------------- | ----------------- | --------------- |
| **Member Administration**   | CRUD All                      | Read All                  | Read All            | Read All          | User Management |
| **National Chairman**       | Read All + Approve Status     | Read All                  | Read All            | Read All          | Read Logs       |
| **National Secretary**      | Read All + Export             | Read All + Export         | Read All            | Export All        | Read Logs       |
| **National Treasurer**      | Read Financial Only           | Read Financial Only       | Read Financial Only | None              | None            |
| **Webmaster**               | Read All                      | CRUD All                  | CRUD All            | CRUD All          | CRUD All        |
| **Tour Commissioner**       | Read All + Export             | CRUD All                  | Read All            | Export All        | None            |
| **Club Magazine Editorial** | Read All + Export             | Read All                  | Read All            | CRUD All          | None            |
| **Webshop Management**      | Read Basic                    | Read All                  | CRUD All            | Read All          | None            |
| **Regional Chairman**       | Read Own Region               | CRUD Own Region           | Read All            | Export Own Region | None            |
| **Regional Secretary**      | Read Own Region + Export      | Read Own Region           | Read All            | Export Own Region | None            |
| **Regional Treasurer**      | Read Own Region Financial     | Read Own Region Financial | Read Financial Only | None              | None            |
| **Regional Volunteer**      | Read Own Region Basic         | Read Own Region           | Read All            | None              | None            |
| **Regular Members**         | Update Own Personal Data Only | Read Public               | Browse Catalog      | None              | None            |

## Authentication Scenarios

### Scenario 1: Jan (National Chairman Role)

**User:** jan.jansen@gmail.com  
**Authentication:** Passkey (Face ID on iPhone)  
**Assigned Roles:** National Chairman roles  
**Permissions:**

- Can view all member data + approve status
- Can view all events, products, communication
- Can view system logs
- Enhanced security: MFA if suspicious activity detected

### Scenario 2: Marie (Regular Member)

**User:** marie.pietersen@hotmail.com  
**Authentication:** Passkey (fingerprint on Android)  
**Assigned Roles:** hdcnLeden (basic member)  
**Permissions:**

- Can only modify own personal data
- Can view public events and browse products
- No administrative access
- No MFA required (streamlined experience)

### Scenario 3: Piet (Multiple Roles)

**User:** piet.klaassen@ziggo.nl  
**Authentication:** Passkey (Windows Hello)  
**Assigned Roles:** Regional Secretary Region 5 + Tour Commissioner  
**Permissions:** Combined permissions from both roles

- Can view/export Region 5 member data (Regional Secretary)
- Can manage all events and export communications (Tour Commissioner)
- Can view all products
- Enhanced security: MFA if suspicious activity detected

### Scenario 4: New User Registration

**User:** new.member@example.com  
**Process:**

1. Email-only registration (no password required)
2. Email verification link sent
3. Guided passkey setup after verification
4. Automatic assignment of basic member role
5. Access to member portal and webshop

## Field-Level Permissions

### Personal Data (Editable by members for own record)

**Note:** Field-level permissions may vary based on membership type and will be clarified during implementation.

Based on Members DynamoDB table structure:

- `voornaam` (first name)
- `achternaam` (last name)
- `tussenvoegsel` (name prefix)
- `initialen` (initials)
- `telefoon` (phone number)
- `straat` (street address)
- `postcode` (postal code)
- `woonplaats` (city)
- `land` (country)
- `email` (email address)
- `nieuwsbrief` (newsletter preference)
- `geboortedatum` (date of birth)
- `geslacht` (gender)

### Motorcycle Data (Editable by members for own record)

- `bouwjaar` (build year)
- `motormerk` (motorcycle brand)
- `motortype` (motorcycle type)
- `kenteken` (license plate)
- `wiewatwaar` (who/what/where information)

### Administrative Data (Admin-only fields)

- `member_id` (system-generated UUID)
- `lidnummer` (membership number)
- `lidmaatschap` (membership type: "gewoon lid", "gezinslid", "donateur", "sponsor", "ere lid")
- `status` (membership status - only Member Administration role can modify)
- `tijdstempel` (member since date)
- `aanmeldingsjaar` (registration year)
- `regio` (region assignment)
- `clubblad` (club magazine subscription)
- `bankrekeningnummer` (bank account number)
- `datum_ondertekening` (signature date)
- `created_at` (record creation timestamp)
- `updated_at` (record update timestamp)

### Notes

- All field names use Dutch naming convention (lowercase with underscores)
- `lidmaatschap` values come from parameter store (not hardcoded)
- `status` values come from parameter store (not hardcoded)
- `regio` values come from parameter store (not hardcoded)

### Parameter Store Examples

Based on actual H-DCN parameter data:

**Regio (Region) values:**

```json
[
  { "id": "1", "value": "Noord-Holland" },
  { "id": "2", "value": "Zuid-Holland" },
  { "id": "3", "value": "Friesland" },
  { "id": "4", "value": "Utrecht" },
  { "id": "5", "value": "Oost" },
  { "id": "6", "value": "Limburg" },
  { "id": "7", "value": "Groningen/Drente" },
  { "id": "8", "value": "Noord-Brabant/Zeeland" },
  { "id": "9", "value": "Duitsland" }
]
```

**Lidmaatschap (Membership Type) values:**

```json
[
  { "id": "1", "value": "Gewoon lid" },
  { "id": "2", "value": "Gezins lid" },
  { "id": "3", "value": "Gezins donateur zonder motor" },
  { "id": "4", "value": "Donateur zonder motor" }
]
```

**Motormerk (Motorcycle Brand) values:**

```json
[
  { "id": "1", "value": "Harley-Davidson" },
  { "id": "2", "value": "Indian" },
  { "id": "3", "value": "Buell" },
  { "id": "4", "value": "Eigenbouw" }
]
```

**Clubblad (Club Magazine) values:**

```json
[
  { "id": "1", "value": "Papier" },
  { "id": "2", "value": "Digitaal" },
  { "id": "3", "value": "Geen" }
]
```

## Key Rules

1. **Passwordless Authentication**: All users authenticate via passkeys with email recovery fallback - no passwords required
2. **Role-Based Access**: Users can have multiple roles with combined permissions
3. **Enhanced Security**: Administrative roles get MFA when suspicious activity is detected
4. **Status Changes**: Only users with Member Administration role can modify member status
5. **Regional Access**: National roles access all regions; regional roles access only their assigned region
6. **Export Rights**: Specific roles can export data based on their permission level
7. **Field Permissions**: Personal data editable by members; administrative data restricted to appropriate roles
8. **Membership Type Variations**: Field-level permissions may vary based on membership type (to be clarified during implementation)

## Technical Implementation

1. **Passwordless Setup**: Users register with email only, verify via email, then set up mandatory passkeys
2. **Role Assignment**: Administrators assign roles to user accounts through role management interface
3. **Permission Calculation**: Roles are translated to specific permissions for UI/API access
4. **Dynamic Updates**: Role changes take effect at next login or within 5 minutes
5. **Existing System Integration**: Parameter system and existing modules updated to work with Cognito authentication
6. **Migration Strategy**: Existing members migrated to Cognito with email verification and passkey setup

## Benefits

- **Enhanced Security**: Passwordless authentication eliminates password-related vulnerabilities
- **User-Friendly**: No passwords to remember, simple biometric authentication
- **Flexible**: Users can have multiple roles with combined permissions
- **Auditability**: All actions are tied to specific user accounts and roles
- **Maintainability**: Role definitions can be updated without code changes
- **Scalability**: New roles can be added by defining permission sets
- **Cost-Effective**: Uses basic Cognito capabilities for simplicity and lower costs

This system provides secure, user-friendly authentication that matches H-DCN's organizational structure while leveraging modern passwordless authentication methods.
