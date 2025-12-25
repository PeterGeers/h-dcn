# H-DCN Role Definition and Permissions Matrix

## Overview

This document defines the complete role-based access control system for H-DCN, mapping organizational functions to Cognito groups (roles) and their associated permissions.

## Role Hierarchy and Precedence

Roles are implemented as AWS Cognito Groups with precedence values (lower numbers = higher precedence):

| Precedence | Role Name                | Description                      |
| ---------- | ------------------------ | -------------------------------- |
| 5          | System_User_Management   | Full user and system management  |
| 10         | Members_CRUD_All         | Complete member data management  |
| 15         | Members_Status_Approve   | Member status approval authority |
| 20         | Members_Read_All         | View all member information      |
| 25         | Events_CRUD_All          | Complete event management        |
| 30         | Events_Read_All          | View all events                  |
| 35         | Products_CRUD_All        | Complete product management      |
| 40         | Products_Read_All        | View all products                |
| 45         | Communication_Export_All | Export all communication data    |
| 50         | Communication_Read_All   | View all communication           |
| 55         | System_Logs_Read         | View system logs                 |
| 100        | hdcnLeden                | Basic member access              |

## Regional Roles (Per Region)

Each region (1-9) has specific roles with regional scope:

| Role Pattern                   | Description                              | Regions |
| ------------------------------ | ---------------------------------------- | ------- |
| Members_Read_Region{N}         | View members in specific region          | 1-9     |
| Members_Export_Region{N}       | Export members from specific region      | 1-9     |
| Events_Read_Region{N}          | View events in specific region           | 1-9     |
| Events_CRUD_Region{N}          | Manage events in specific region         | 1-9     |
| Communication_Export_Region{N} | Export communication for specific region | 1-9     |

### Region Mapping

| Region ID | Region Name           |
| --------- | --------------------- |
| 1         | Noord-Holland         |
| 2         | Zuid-Holland          |
| 3         | Friesland             |
| 4         | Utrecht               |
| 5         | Oost                  |
| 6         | Limburg               |
| 7         | Groningen/Drente      |
| 8         | Noord-Brabant/Zeeland |
| 9         | Duitsland             |

## Organizational Function to Role Mapping

### General Board Functions

#### Member Administration

**Organizational Function**: Complete member management authority
**Assigned Roles**:

- `Members_CRUD_All` (precedence: 10)
- `Events_Read_All` (precedence: 30)
- `Products_Read_All` (precedence: 40)
- `Communication_Read_All` (precedence: 50)
- `System_User_Management` (precedence: 5)

**Effective Permissions**:

- Full CRUD access to all member data
- Can modify member status and administrative fields
- View all events, products, and communication
- Manage user accounts and role assignments
- Access to user management functions

#### National Chairman

**Organizational Function**: Strategic oversight and member status approval
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Members_Status_Approve` (precedence: 15)
- `Events_Read_All` (precedence: 30)
- `Products_Read_All` (precedence: 40)
- `Communication_Read_All` (precedence: 50)
- `System_Logs_Read` (precedence: 55)

**Effective Permissions**:

- View all member data across all regions
- Approve/reject member status changes
- View all events, products, and communication
- Access to system logs for oversight
- Cannot modify member data directly (approval only)

#### National Secretary

**Organizational Function**: Administrative support and data export
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Communication_Export_All` (precedence: 45)
- `Events_Read_All` (precedence: 30)
- `Products_Read_All` (precedence: 40)
- `System_Logs_Read` (precedence: 55)

**Effective Permissions**:

- View all member data
- Export member data for communications
- View all events and products
- Export communication data
- Access to system logs

#### National Treasurer

**Organizational Function**: Financial oversight and reporting
**Assigned Roles**:

- `Members_Read_Financial` (precedence: 25) _[To be created]_
- `Events_Read_Financial` (precedence: 35) _[To be created]_
- `Products_Read_Financial` (precedence: 45) _[To be created]_

**Effective Permissions**:

- View financial data only (payment status, membership fees)
- Access to financial reports
- No access to personal member data
- No communication or system access

#### Vice-Chairman

**Organizational Function**: Support to National Chairman
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Events_Read_All` (precedence: 30)
- `Products_Read_All` (precedence: 40)
- `Communication_Read_All` (precedence: 50)

**Effective Permissions**:

- View all member data (no approval authority)
- View all events, products, and communication
- No system administration access

### Supporting Functions

#### Webmaster

**Organizational Function**: Complete system and content management
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Events_CRUD_All` (precedence: 25)
- `Products_CRUD_All` (precedence: 35)
- `Communication_CRUD_All` (precedence: 40) _[To be created]_
- `System_CRUD_All` (precedence: 1) _[To be created]_

**Effective Permissions**:

- View all member data
- Full CRUD access to events, products, and communication
- Complete system administration access
- Website and technical system management

#### Tour Commissioner

**Organizational Function**: Event management and member communication
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Communication_Export_All` (precedence: 45)
- `Events_CRUD_All` (precedence: 25)
- `Products_Read_All` (precedence: 40)

**Effective Permissions**:

- View all member data for event planning
- Full event management (create, update, delete)
- Export member data for event communications
- View products for event coordination

#### Club Magazine Editorial

**Organizational Function**: Content creation and member communication
**Assigned Roles**:

- `Members_Read_All` (precedence: 20)
- `Communication_Export_All` (precedence: 45)
- `Communication_CRUD_All` (precedence: 40) _[To be created]_
- `Events_Read_All` (precedence: 30)
- `Products_Read_All` (precedence: 40)

**Effective Permissions**:

- View all member data for content creation
- Full communication management
- Export member data for magazine distribution
- View events and products for editorial content

#### Webshop Management

**Organizational Function**: Product and order management
**Assigned Roles**:

- `Members_Read_Basic` (precedence: 30) _[To be created]_
- `Products_CRUD_All` (precedence: 35)
- `Events_Read_All` (precedence: 30)
- `Communication_Read_All` (precedence: 50)

**Effective Permissions**:

- View basic member data (for order processing)
- Full product management
- View events for product coordination
- View communication for customer service

### Regional Functions

#### Regional Chairman (per region)

**Organizational Function**: Regional leadership and event management
**Assigned Roles** (example for Region 1):

- `Members_Read_Region1` (precedence: 25)
- `Events_CRUD_Region1` (precedence: 30)
- `Products_Read_All` (precedence: 40)
- `Communication_Export_Region1` (precedence: 50)

**Effective Permissions**:

- View member data for assigned region only
- Full event management for assigned region
- View all products
- Export communication data for assigned region

#### Regional Secretary (per region)

**Organizational Function**: Regional administrative support
**Assigned Roles** (example for Region 1):

- `Members_Read_Region1` (precedence: 25)
- `Members_Export_Region1` (precedence: 30)
- `Events_Read_Region1` (precedence: 35)
- `Products_Read_All` (precedence: 40)
- `Communication_Export_Region1` (precedence: 50)

**Effective Permissions**:

- View and export member data for assigned region
- View events for assigned region
- View all products
- Export communication data for assigned region

#### Regional Treasurer (per region)

**Organizational Function**: Regional financial management
**Assigned Roles** (example for Region 1):

- `Members_Read_Region1_Financial` (precedence: 30) _[To be created]_
- `Events_Read_Region1_Financial` (precedence: 35) _[To be created]_
- `Products_Read_Financial` (precedence: 45) _[To be created]_

**Effective Permissions**:

- View financial data for assigned region only
- Access to regional financial reports
- No access to personal member data
- No communication access

#### Regional Volunteer (per region)

**Organizational Function**: Regional support and basic member assistance
**Assigned Roles** (example for Region 1):

- `Members_Read_Region1_Basic` (precedence: 35) _[To be created]_
- `Events_Read_Region1` (precedence: 35)
- `Products_Read_All` (precedence: 40)

**Effective Permissions**:

- View basic member data for assigned region
- View events for assigned region
- View all products
- No export or modification capabilities

### Basic Members

#### Regular Members (hdcnLeden)

**Organizational Function**: Basic membership access
**Assigned Roles**:

- `hdcnLeden` (precedence: 100)

**Effective Permissions**:

- Update own personal and motorcycle data only
- View public events
- Browse product catalog
- Access webshop functionality
- No access to other members' data

## Detailed Permissions Matrix

### Member Data Permissions

| Role                     | Own Data | Region Data | All Data | Financial | Status  | Export |
| ------------------------ | -------- | ----------- | -------- | --------- | ------- | ------ |
| hdcnLeden                | CRUD     | -           | -        | -         | -       | -      |
| Members_Read_All         | Read     | Read        | Read     | -         | -       | -      |
| Members_CRUD_All         | CRUD     | CRUD        | CRUD     | Read      | CRUD    | Export |
| Members_Status_Approve   | Read     | Read        | Read     | -         | Approve | -      |
| Members_Export_All       | Read     | Read        | Read     | -         | -       | Export |
| Members_Read_Region{N}   | Read     | Read        | -        | -         | -       | -      |
| Members_Export_Region{N} | Read     | Read        | -        | -         | -       | Export |
| Members_Read_Financial   | -        | -           | -        | Read      | -       | -      |
| Members_Read_Basic       | Read     | -           | -        | -         | -       | -      |

### Events Permissions

| Role                  | Public Events | Region Events | All Events | Financial | CRUD | Export |
| --------------------- | ------------- | ------------- | ---------- | --------- | ---- | ------ |
| hdcnLeden             | Read          | -             | -          | -         | -    | -      |
| Events_Read_All       | Read          | Read          | Read       | -         | -    | -      |
| Events_CRUD_All       | Read          | Read          | Read       | Read      | CRUD | Export |
| Events_Read_Region{N} | Read          | Read          | -          | -         | -    | -      |
| Events_CRUD_Region{N} | Read          | Read          | -          | Read      | CRUD | Export |
| Events_Read_Financial | -             | -             | -          | Read      | -    | -      |

### Products Permissions

| Role                    | Catalog | All Products | Financial | CRUD | Export |
| ----------------------- | ------- | ------------ | --------- | ---- | ------ |
| hdcnLeden               | Browse  | -            | -         | -    | -      |
| Products_Read_All       | Read    | Read         | -         | -    | -      |
| Products_CRUD_All       | Read    | Read         | Read      | CRUD | Export |
| Products_Read_Financial | -       | -            | Read      | -    | -      |

### Communication Permissions

| Role                           | Own Comm | Region Comm | All Comm | CRUD | Export |
| ------------------------------ | -------- | ----------- | -------- | ---- | ------ |
| hdcnLeden                      | -        | -           | -        | -    | -      |
| Communication_Read_All         | Read     | Read        | Read     | -    | -      |
| Communication_CRUD_All         | Read     | Read        | Read     | CRUD | Export |
| Communication_Export_All       | Read     | Read        | Read     | -    | Export |
| Communication_Export_Region{N} | Read     | Read        | -        | -    | Export |

### System Administration Permissions

| Role                   | User Mgmt | Logs | System Config | Full Admin |
| ---------------------- | --------- | ---- | ------------- | ---------- |
| hdcnLeden              | -         | -    | -             | -          |
| System_User_Management | CRUD      | -    | -             | -          |
| System_Logs_Read       | -         | Read | -             | -          |
| System_CRUD_All        | CRUD      | Read | CRUD          | CRUD       |

## Role Assignment Rules

### Automatic Role Assignment

1. **New Members**: Automatically assigned `hdcnLeden` role upon account creation
2. **Email Domain Based**: Users with `@h-dcn.nl` email addresses are flagged for administrative role review
3. **Migration**: Existing members automatically assigned `hdcnLeden` role during migration

### Manual Role Assignment

1. **Administrative Roles**: Must be manually assigned by users with `System_User_Management` role
2. **Regional Roles**: Assigned based on member's region and organizational function
3. **Multiple Roles**: Users can have multiple roles with combined permissions
4. **Role Validation**: System validates role combinations for conflicts

### Role Inheritance and Conflicts

1. **Additive Permissions**: Multiple roles combine permissions (union, not intersection)
2. **Precedence Rules**: Higher precedence roles (lower numbers) take priority for conflicting permissions
3. **Regional Scope**: Regional roles are limited to their assigned region
4. **Administrative Override**: System administration roles can override regional restrictions

## Security and Compliance

### MFA Requirements

| Role Category  | MFA Required | Trigger             |
| -------------- | ------------ | ------------------- |
| hdcnLeden      | No           | Never               |
| Regional Roles | Yes          | Suspicious activity |
| National Roles | Yes          | Suspicious activity |
| System Admin   | Yes          | Always              |

### Audit Requirements

1. **Role Changes**: All role assignments/removals are logged with user, timestamp, and reason
2. **Permission Usage**: Administrative actions are logged with role context
3. **Data Access**: Member data access by administrative roles is logged
4. **Export Activities**: All data exports are logged with user, filters, and purpose

### Data Privacy

1. **Regional Restrictions**: Regional roles cannot access other regions' data
2. **Financial Data**: Separate permissions for financial information access
3. **Personal Data**: Administrative access to personal data is logged and auditable
4. **Export Controls**: Data export permissions are strictly controlled and logged

## Implementation Notes

### Roles Marked _[To be created]_

The following roles need to be created during implementation:

1. `Members_Read_Financial` - Access to financial data only
2. `Members_Read_Basic` - Basic member information only
3. `Communication_CRUD_All` - Full communication management
4. `System_CRUD_All` - Complete system administration
5. Regional financial roles: `Members_Read_Region{N}_Financial`
6. Regional basic roles: `Members_Read_Region{N}_Basic`
7. Regional event financial roles: `Events_Read_Region{N}_Financial`

### Role Naming Convention

- **Scope**: `Members`, `Events`, `Products`, `Communication`, `System`
- **Permission**: `Read`, `CRUD`, `Export`, `Approve`
- **Restriction**: `All`, `Region{N}`, `Financial`, `Basic`
- **Format**: `{Scope}_{Permission}_{Restriction}`

### Testing Strategy

1. **Role Assignment Testing**: Verify each organizational function receives correct role combination
2. **Permission Calculation**: Test permission combinations for users with multiple roles
3. **Regional Restrictions**: Verify regional roles cannot access other regions
4. **Administrative Actions**: Test all administrative functions with appropriate roles
5. **Security Testing**: Verify MFA triggers and audit logging work correctly

This role definition provides the foundation for implementing the complete H-DCN role-based access control system with proper security, auditability, and organizational alignment.
