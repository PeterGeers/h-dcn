# H-DCN Role Permission Combinations

## Overview

This document defines the standard permission combinations for common H-DCN organizational functions. These combinations represent the typical role assignments that users receive based on their organizational responsibilities.

## Common Organizational Function Combinations

### Member Administration

**Role Combination:** [`Members_CRUD_All`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_User_Management`]

**Description:** Full member management capabilities with system administration rights
**Typical Users:** Board members responsible for member administration
**Permissions:**

- Complete member data management (create, read, update, delete)
- View all events and products
- Access to all communication data
- User management and system administration capabilities

### National Chairman

**Role Combination:** [`Members_Read_All`, `Members_Status_Approve`, `Events_Read_All`, `Products_Read_All`, `Communication_Read_All`, `System_Logs_Read`]

**Description:** Oversight and approval authority across all organizational areas
**Typical Users:** National Chairman and senior leadership
**Permissions:**

- View all member data across all regions
- Approve member status changes
- View all events, products, and communications
- Access to system logs for oversight

### Webmaster

**Role Combination:** [`Members_Read_All`, `Events_CRUD_All`, `Products_CRUD_All`, `Communication_CRUD_All`, `System_CRUD_All`]

**Description:** Technical administration with full system management capabilities
**Typical Users:** Technical administrators and webmasters
**Permissions:**

- View all member data
- Full management of events, products, and communications
- Complete system administration rights

### Regular Members

**Role Combination:** [`hdcnLeden`]

**Description:** Basic member access for personal data management and webshop
**Typical Users:** All H-DCN members
**Permissions:**

- Update own personal and motorcycle information
- Access to webshop and public events
- Basic member portal functionality

## Implementation Notes

1. **Multiple Role Assignment:** Users can be assigned multiple roles, with permissions being additive
2. **Role Precedence:** Lower precedence numbers take priority in case of conflicts
3. **Regional Variations:** Regional roles follow similar patterns but with geographic restrictions
4. **Dynamic Assignment:** Role combinations can be modified based on organizational needs

## Usage in System

These combinations are used in:

- **Role Assignment Interface:** Predefined templates for common organizational functions
- **Permission Calculation:** Backend systems combine individual role permissions
- **UI Rendering:** Frontend components show/hide features based on combined permissions
- **Audit Logging:** Track which role combinations are assigned to users

## Maintenance

This document should be updated when:

- New organizational functions are identified
- Role definitions change
- Permission requirements evolve
- System capabilities expand

Last Updated: December 25, 2024
