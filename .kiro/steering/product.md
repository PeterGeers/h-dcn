# Product Overview

H-DCN (Harley-Davidson Club Nederland) is a member portal and webshop application for the Dutch Harley-Davidson motorcycle club. It provides:

- **Member management**: Registration, profiles, membership types, regional grouping
- **Webshop**: Product catalog, shopping cart, orders, payments (Stripe integration)
- **Event management**: Club events with member participation
- **Admin dashboard**: Cognito user administration, role/permission management, member reporting and exports
- **Authentication**: AWS Cognito with Google Workspace SSO, role-based access control with regional permissions

The portal is hosted at portal.h-dcn.nl and serves both regular members (self-service profile, webshop) and administrators (member management, reporting, user administration).

## Key Domain Concepts

- **Members** have a `regio` (region) field used for regional access filtering
- **Memberships** are typed (e.g., regular, honorary) and tracked separately from member profiles
- **Permissions** are role-based with regional scoping (users may only access members in their allowed regions)
- **Orders** go through a status workflow and can generate PDF confirmations
- The organization short name is "H-DCN"
