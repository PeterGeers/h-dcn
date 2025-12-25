---
inclusion: manual
---

# H-DCN Dashboard Product Overview

## Product Description

H-DCN Dashboard is a comprehensive full-stack web application for Harley-Davidson Club Nederland (H-DCN) providing club management, e-commerce, and member administration with mobile-responsive design.

## Core Features

- **Member Management**: Complete CRUD operations for club members with regional access controls
- **E-commerce Platform**: Webshop with Stripe payment integration and order management
- **Event Management**: Club events creation, tracking, and participation management
- **Authentication & Authorization**: AWS Cognito-based user management with role-based access control
- **Mobile-First Design**: Responsive UI optimized for all devices using Chakra UI

## User Roles & Access Levels

- **No Groups**: Membership registration only
- **hdcnLeden**: Webshop access and profile management
- **hdcnRegio\_\***: Regional member administration (read-only)
- **hdcnAdmins**: Full system access including user management, events, products, and system configuration

## Key Business Logic

- Dynamic membership registration forms
- Regional access control for member data
- Function-level permissions via parameter store
- Automated payment tracking and order processing
- Multi-level product categorization system
