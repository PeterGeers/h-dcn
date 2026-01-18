# H-DCN Backend API Documentation

**Base URL:** `https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod`

## Authentication Configuration

**Cognito User Pool ID:** `eu-west-1_OAT3oPCIm`  
**Cognito Client ID:** `7p5t7sjl2s1rcu1emn85h20qeh`  
**Cognito Domain:** `https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com`

### User Status

✅ **All 74 users are now in CONFIRMED status** - ready for passwordless authentication

### Available Roles

- **hdcnLeden** - Basic H-DCN member role (access to personal data and webshop)
- **Members_CRUD_All** - Full member management permissions
- **System_User_Management** - System user management permissions
- **Events_CRUD_All** - Full event management permissions
- **Products_CRUD_All** - Full product management permissions

## Product APIs

- `POST /insert-product/` - Create product
  ```json
  { "id": "prod_001", "name": "Product Name", "price": 29.99, "image": "url" }
  ```
- `GET /getproduct-byid/{id}` - Get product by ID
- `GET /scan-product/` - List all products
- `PUT /update-product/{id}` - Update product
  ```json
  { "name": "Updated Name", "price": 39.99 }
  ```
- `DELETE /delete-product/{id}` - Delete product

## Member APIs

- `POST /members` - Create member
  ```json
  { "name": "John Doe", "email": "john@example.com", "phone": "123456789" }
  ```
- `GET /members` - Get all members
- `GET /members/{id}` - Get member by ID
- `PUT /members/{id}` - Update member
  ```json
  { "name": "Jane Doe", "email": "jane@example.com" }
  ```
- `DELETE /members/{id}` - Delete member

## Payment APIs

- `POST /payments` - Create payment
  ```json
  {
    "member_id": "mem_001",
    "amount": "50.00",
    "payment_type": "membership",
    "description": "Annual fee"
  }
  ```
- `GET /payments` - Get all payments
- `GET /payments/{payment_id}` - Get payment by ID
- `PUT /payments/{payment_id}` - Update payment
  ```json
  { "amount": "75.00", "description": "Updated payment amount" }
  ```
- `DELETE /payments/{payment_id}` - Delete payment
- `GET /payments/member/{member_id}` - Get member payments

## Event APIs

- `POST /events` - Create event
  ```json
  {
    "naam": "Voorjaarsrit",
    "datum_van": "2024-04-15",
    "locatie": "Café De Biker"
  }
  ```
- `GET /events` - Get all events
- `GET /events/{event_id}` - Get event by ID
- `PUT /events/{event_id}` - Update event
  ```json
  { "naam": "Updated Event", "aantal_deelnemers": 30 }
  ```
- `DELETE /events/{event_id}` - Delete event

## Membership APIs

- `GET /memberships` - Get all membership types
- `POST /memberships` - Create membership type
  ```json
  {
    "name": "Premium",
    "price": 99.99,
    "duration_months": 12,
    "description": "Premium membership"
  }
  ```
  Response includes auto-generated `membership_type_id`
- `GET /memberships/{id}` - Get membership by ID
- `PUT /memberships/{id}` - Update membership type
  ```json
  {
    "name": "Premium Plus",
    "price": 149.99,
    "description": "Enhanced premium membership"
  }
  ```
- `DELETE /memberships/{id}` - Delete membership type

## Cart APIs

- `POST /carts` - Create cart
  ```json
  { "customer_id": "cust_001", "items": [] }
  ```
- `GET /carts/{cart_id}` - Get cart
- `PUT /carts/{cart_id}/items` - Update cart items
  ```json
  {
    "items": [{ "product_id": "prod_001", "quantity": 2 }],
    "total_amount": 59.98
  }
  ```
- `DELETE /carts/{cart_id}` - Clear cart

## Order APIs

- `POST /orders` - Create order
  ```json
  { "customer_id": "cust_001", "items": [], "total_amount": 100.0 }
  ```
- `GET /orders` - Get all orders
- `GET /orders/{order_id}` - Get order by ID
- `PUT /orders/{order_id}/status` - Update order
  ```json
  { "status": "shipped", "tracking_number": "TRK123" }
  ```
- `GET /orders/customer/{customer_id}` - Get customer orders

## Parameter APIs

- `POST /parameters` - Create parameter
  ```json
  { "name": "new_param", "value": "param_value", "description": "Description" }
  ```
- `GET /parameters` - Get all parameters
- `GET /parameters/{id}` - Get parameter by ID
- `GET /parameters/name/{name}` - Get parameter by name
- `PUT /parameters/{id}` - Update parameter
  ```json
  { "value": "updated_value", "description": "Updated description" }
  ```
- `DELETE /parameters/{id}` - Delete parameter

## Cognito Admin APIs

- `GET /cognito/users` - List all users
- `POST /cognito/users` - Create user
  ```json
  {
    "username": "john_doe",
    "email": "john@example.com",
    "tempPassword": "WelkomHDCN2024!"
  }
  ```
- `PUT /cognito/users/{username}` - Update user attributes
  ```json
  { "attributes": { "given_name": "John", "family_name": "Doe" } }
  ```
- `DELETE /cognito/users/{username}` - Delete user
- `GET /cognito/groups` - List all groups
- `POST /cognito/groups` - Create group
  ```json
  { "groupName": "admins", "description": "Administrator group" }
  ```
- `DELETE /cognito/groups/{groupName}` - Delete group
- `GET /cognito/groups/{groupName}/users` - Get users in group
- `POST /cognito/users/{username}/groups/{groupName}` - Add user to group
- `DELETE /cognito/users/{username}/groups/{groupName}` - Remove user from group
- `GET /cognito/users/{username}/groups` - Get user's groups

- `POST /cognito/groups/import` - Bulk import groups

  ```json
  {
    "groups": [
      { "groupName": "hdcnLeden", "description": "HDCN Members" },
      { "groupName": "hdcnBestuur", "description": "Board Members" }
    ]
  }
  ```

- `GET /cognito/pool` - Get user pool information

## Available Parameters

- `regio` - Regional data (Noord-Holland, Zuid-Holland, etc.)
- `lidmaatschap` - Membership types
- `motormerk` - Motor brands (Harley-Davidson, Indian, etc.)
- `clubblad` - Newsletter preferences
- `wiewatwaar` - How members found the club
- `productgroepen` - Product categories with subcategories
- `api_base_url` - API base URL configuration

## Notes

- All POST/PUT requests require `Content-Type: application/json`
- All endpoints support CORS with `Access-Control-Allow-Origin: *`
- Timestamps (`created_at`, `updated_at`, `payment_date`) are automatically managed
- IDs are auto-generated for create operations

**Total: 53 API endpoints**

## Migration Tools

For bulk Cognito operations during migration, use:

- `cognito_bulk_operations.py` - Direct Python script
- `cognito_bulk_cli.ps1` - PowerShell/AWS CLI script

These bypass API Gateway and work directly with AWS Cognito.
