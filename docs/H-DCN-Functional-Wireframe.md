# H-DCN Functional Wireframe

## Target Platform: TypeScript / Python / MySQL

---

## 1. Application Overview

The H-DCN (Harley-Davidson Club Nederland) Portal is a membership management and e-commerce platform serving a motorcycle club with ~500+ members across multiple Dutch regions.

### Target Architecture (New Platform)

| Layer       | Technology             | Purpose                        |
| ----------- | ---------------------- | ------------------------------ |
| Frontend    | TypeScript + React     | SPA with role-based UI         |
| Backend API | Python (FastAPI/Flask) | REST API services              |
| Database    | MySQL                  | Relational data storage        |
| Auth        | JWT + OAuth 2.0        | Authentication & authorization |
| Payments    | Stripe                 | E-commerce payments            |
| Storage     | S3-compatible          | File/image uploads             |

---

## 2. Functional Modules

```
+------------------------------------------------------------------+
|                        H-DCN PORTAL                               |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  |  AUTHENTICATION  |  |    DASHBOARD     |  |   MY ACCOUNT     | |
|  |  - Passwordless  |  |  - Role-based    |  |  - Profile       | |
|  |  - Google OAuth  |  |  - Module cards  |  |  - Preferences   | |
|  |  - Email verify  |  |  - Welcome msg   |  |  - Password      | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | MEMBER MGMT      |  | EVENT MGMT       |  | WEBSHOP          | |
|  | - CRUD members   |  | - CRUD events    |  | - Product catalog| |
|  | - Regional filter|  | - Attendance     |  | - Shopping cart   | |
|  | - Bulk import    |  | - Finance track  |  | - Checkout/Pay   | |
|  | - Export (CSV)   |  | - Analytics      |  | - Order history  | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+  +------------------+ |
|  | PRODUCT MGMT     |  | MEMBERSHIP TYPES |  | ADVANCED EXPORTS | |
|  | - Inventory      |  | - Type CRUD      |  | - CSV/XLSX/PDF   | |
|  | - Categories     |  | - Pricing        |  | - Custom filters | |
|  | - Image upload   |  | - Benefits       |  | - Analytics      | |
|  +------------------+  +------------------+  +------------------+ |
|                                                                    |
|  +------------------+  +------------------+                       |
|  | USER ADMIN       |  | SYSTEM CONFIG    |                       |
|  | - User CRUD      |  | - Parameters     |                       |
|  | - Role assign    |  | - Email templates|                       |
|  | - Group mgmt     |  | - Org settings   |                       |
|  +------------------+  +------------------+                       |
+------------------------------------------------------------------+
```

---

## 3. User Roles & Access Matrix

### Role Hierarchy

```
System_CRUD (superadmin)
  |
  +-- System_User_Management
  |
  +-- Members_CRUD + Regio_All (national member admin)
  |     |
  |     +-- Members_CRUD + Regio_[Name] (regional member admin)
  |     |
  |     +-- Members_Read + Regio_[Name] (regional viewer)
  |
  +-- Events_CRUD + Regio_All (national event admin)
  |
  +-- Products_CRUD / Webshop_Management
  |
  +-- hdcnLeden (basic member)
  |
  +-- verzoek_lid (applicant)
```

### Access Matrix

| Module           | verzoek_lid | hdcnLeden | Members_Read | Members_CRUD | Events_CRUD | Products_CRUD | System_CRUD |
| ---------------- | :---------: | :-------: | :----------: | :----------: | :---------: | :-----------: | :---------: |
| Application Form |      W      |     -     |      -       |      -       |      -      |       -       |      -      |
| My Account       |      R      |    RW     |      RW      |      RW      |     RW      |      RW       |     RW      |
| Webshop          |      -      |    RW     |      RW      |      RW      |     RW      |      RW       |     RW      |
| Member Admin     |      -      |     -     |      R       |      RW      |      -      |       -       |     RW      |
| Event Admin      |      -      |     -     |      -       |      -       |     RW      |       -       |     RW      |
| Product Admin    |      -      |     -     |      -       |      -       |      -      |      RW       |     RW      |
| Membership Types |      -      |     -     |      -       |      RW      |      -      |       -       |     RW      |
| User Admin       |      -      |     -     |      -       |      -       |      -      |       -       |     RW      |
| System Config    |      -      |     -     |      -       |      -       |      -      |       -       |     RW      |
| Advanced Exports |      -      |     -     |      -       |      -       |      -      |      RW       |     RW      |

R = Read, W = Write, RW = Read+Write

---

## 4. Screen Wireframes

### 4.1 Authentication Flow

```
+-----------------------------------------------+
|              H-DCN PORTAL LOGIN                |
+-----------------------------------------------+
|                                                |
|          [H-DCN Logo]                          |
|                                                |
|    +------------------------------------+      |
|    |  Sign in with Passkey (WebAuthn)   |      |
|    +------------------------------------+      |
|                                                |
|    +------------------------------------+      |
|    |  Sign in with Google               |      |
|    +------------------------------------+      |
|                                                |
|    ─────────── or ───────────                  |
|                                                |
|    Email: [________________________]           |
|    [  Send verification code  ]                |
|                                                |
|    New member? [Register here]                 |
+-----------------------------------------------+
```

### 4.2 Dashboard (Role-Based)

```
+-----------------------------------------------+
| [H-DCN Portal]              [User ▼] [Logout] |
+-----------------------------------------------+
|                                                |
|  Welkom, {Voornaam} {Achternaam}!              |
|  Kies een applicatie om te starten:            |
|                                                |
|  +----------+  +----------+  +----------+     |
|  | 👤        |  | 🛒        |  | 👥        |   |
|  | Mijn     |  | Webshop  |  | Leden-   |   |
|  | Gegevens |  |          |  | admin    |   |
|  +----------+  +----------+  +----------+     |
|                                                |
|  +----------+  +----------+  +----------+     |
|  | 📅        |  | 📦        |  | 🎫        |   |
|  | Evene-   |  | Product  |  | Lidmaat- |   |
|  | menten   |  | Beheer   |  | schappen |   |
|  +----------+  +----------+  +----------+     |
|                                                |
|  +----------+                                  |
|  | 🚀        |                                  |
|  | Exports  |                                  |
|  +----------+                                  |
+-----------------------------------------------+
```

### 4.3 Member Administration

```
+-----------------------------------------------+
| [← Dashboard]  Ledenadministratie    [User ▼] |
+-----------------------------------------------+
| Filters:                                       |
| [Region ▼] [Status ▼] [Type ▼] [Search___]   |
| [Export CSV] [Export XLSX] [+ Nieuw Lid]       |
+-----------------------------------------------+
| # | Naam          | Email        | Regio | St |
|---|---------------|--------------|-------|----|
| 1 | Jan de Vries  | jan@...      | Utrecht| ✓ |
| 2 | Piet Jansen   | piet@...     | Limburg| ✓ |
| 3 | Kees Bakker   | kees@...     | Utrecht| ⏳|
|   |               |              |       |    |
| [◀ Prev]  Pagina 1 van 12  [Next ▶]         |
+-----------------------------------------------+

--- Member Detail Modal ---
+-----------------------------------------------+
|  Lid Bewerken                          [X]    |
+-----------------------------------------------+
| Voornaam:    [Jan              ]               |
| Achternaam:  [de Vries         ]               |
| Email:       [jan@example.nl   ]               |
| Telefoon:    [06-12345678      ]               |
| Regio:       [Utrecht        ▼]               |
| Lidmaatschap:[Volledig lid   ▼]               |
| Status:      [Actief         ▼]               |
| Lid sinds:   [2020-03-15      ]               |
|                                                |
| Adres:                                         |
| Straat:      [Hoofdstraat 1    ]               |
| Postcode:    [3511 AB          ]               |
| Plaats:      [Utrecht          ]               |
|                                                |
| [Annuleren]              [Opslaan]             |
+-----------------------------------------------+
```

### 4.4 Webshop

```
+-----------------------------------------------+
| [← Dashboard]  Webshop         [🛒 3] [User▼]|
+-----------------------------------------------+
| Categorieën: [Alle ▼]  Zoeken: [________]     |
+-----------------------------------------------+
|                                                |
| +--------+  +--------+  +--------+            |
| |[Image] |  |[Image] |  |[Image] |            |
| | T-Shirt|  | Pet    |  | Jas    |            |
| | €29.95 |  | €19.95 |  | €89.95 |            |
| |[In kar]|  |[In kar]|  |[In kar]|            |
| +--------+  +--------+  +--------+            |
|                                                |
| +--------+  +--------+                         |
| |[Image] |  |[Image] |                         |
| | Patch  |  | Mok    |                         |
| | €12.50 |  | €14.95 |                         |
| |[In kar]|  |[In kar]|                         |
| +--------+  +--------+                         |
+-----------------------------------------------+

--- Shopping Cart ---
+-----------------------------------------------+
|  Winkelwagen                           [X]    |
+-----------------------------------------------+
| Product        | Aantal | Prijs    | Subtotaal|
|----------------|--------|----------|----------|
| T-Shirt XL     | [2]    | €29.95   | €59.90   |
| Pet zwart      | [1]    | €19.95   | €19.95   |
|                |        |          |----------|
|                |        | Totaal:  | €79.85   |
+-----------------------------------------------+
| [Verder winkelen]          [Afrekenen →]       |
+-----------------------------------------------+
```

### 4.5 Event Administration

```
+-----------------------------------------------+
| [← Dashboard]  Evenementen           [User ▼] |
+-----------------------------------------------+
| [+ Nieuw Evenement]  [Export]                  |
| Filter: [Komend ▼] [Regio ▼] [Search___]     |
+-----------------------------------------------+
| Datum      | Evenement        | Locatie  | 👥 |
|------------|------------------|----------|-----|
| 2026-06-15 | Zomerrit Utrecht | Utrecht  | 45  |
| 2026-07-20 | Nationale Dag    | A'dam    | 180 |
| 2026-08-10 | Regio BBQ        | Limburg  | 32  |
+-----------------------------------------------+

--- Event Detail/Edit ---
+-----------------------------------------------+
| Evenement Bewerken                     [X]    |
+-----------------------------------------------+
| Titel:       [Zomerrit Utrecht         ]      |
| Datum:       [2026-06-15    ] [14:00]         |
| Einddatum:   [2026-06-15    ] [18:00]         |
| Locatie:     [Parkeerplaats A2         ]      |
| Regio:       [Utrecht              ▼]         |
| Beschrijving:                                  |
| [                                      ]      |
| [  Mooie rit door het Utrechtse...    ]      |
| [                                      ]      |
| Max deelnemers: [50    ]                      |
| Kosten:         [€15.00]                      |
|                                                |
| [Annuleren]              [Opslaan]             |
+-----------------------------------------------+
```

### 4.6 New Member Application

```
+-----------------------------------------------+
|              AANMELDEN ALS LID                 |
+-----------------------------------------------+
|                                                |
| Stap 1 van 3: Persoonlijke Gegevens           |
| ═══════════════●─────────────────────          |
|                                                |
| Voornaam*:     [________________]              |
| Achternaam*:   [________________]              |
| Geboortedatum: [____-__-__      ]              |
| Email*:        [________________]              |
| Telefoon:      [________________]              |
|                                                |
| Adres                                          |
| Straat*:       [________________]              |
| Huisnummer*:   [____]                          |
| Postcode*:     [______]                        |
| Plaats*:        [________________]              |
|                                                |
| Motor informatie                               |
| Merk:          [Harley-Davidson ▼]             |
| Model:         [________________]              |
| Bouwjaar:      [____]                          |
|                                                |
| [Volgende stap →]                              |
+-----------------------------------------------+
```

### 4.7 My Account / Profile

```
+-----------------------------------------------+
| [← Dashboard]  Mijn Gegevens         [User ▼]|
+-----------------------------------------------+
|                                                |
| +------------------------------------------+  |
| | Persoonlijke Informatie          [Bewerk] |  |
| |------------------------------------------|  |
| | Naam:     Jan de Vries                    |  |
| | Email:    jan@example.nl                  |  |
| | Telefoon: 06-12345678                     |  |
| | Adres:    Hoofdstraat 1, Utrecht          |  |
| +------------------------------------------+  |
|                                                |
| +------------------------------------------+  |
| | Lidmaatschap                              |  |
| |------------------------------------------|  |
| | Type:     Volledig Lid                    |  |
| | Sinds:    15 maart 2020                   |  |
| | Regio:    Utrecht                         |  |
| | Status:   Actief ✓                        |  |
| +------------------------------------------+  |
|                                                |
| +------------------------------------------+  |
| | Mijn Bestellingen                [Alles] |  |
| |------------------------------------------|  |
| | #1234 | 2026-04-20 | €79.85 | Verzonden |  |
| | #1198 | 2026-03-10 | €29.95 | Afgeleverd|  |
| +------------------------------------------+  |
+-----------------------------------------------+
```

---

## 5. MySQL Database Schema (Target Platform)

```sql
-- Core tables for the new MySQL platform

-- Users & Authentication
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    given_name VARCHAR(100),
    family_name VARCHAR(100),
    auth_provider ENUM('local', 'google', 'passkey') DEFAULT 'local',
    auth_provider_id VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    status ENUM('active', 'inactive', 'pending', 'suspended') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Role-based access control
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    role_type ENUM('permission', 'region', 'system', 'member') NOT NULL
);

CREATE TABLE user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INT,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Members
CREATE TABLE members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE,
    member_number VARCHAR(20) UNIQUE,
    given_name VARCHAR(100) NOT NULL,
    family_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    street VARCHAR(255),
    house_number VARCHAR(10),
    postal_code VARCHAR(10),
    city VARCHAR(100),
    region VARCHAR(50),
    membership_type_id INT,
    status ENUM('active', 'pending', 'inactive', 'rejected') DEFAULT 'pending',
    member_since DATE,
    motorcycle_brand VARCHAR(100),
    motorcycle_model VARCHAR(100),
    motorcycle_year INT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (membership_type_id) REFERENCES membership_types(id)
);

-- Membership Types
CREATE TABLE membership_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    duration_months INT DEFAULT 12,
    benefits TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events
CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_date DATETIME NOT NULL,
    end_date DATETIME,
    location VARCHAR(255),
    region VARCHAR(50),
    max_participants INT,
    cost DECIMAL(10,2) DEFAULT 0,
    status ENUM('draft', 'published', 'cancelled', 'completed') DEFAULT 'draft',
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE TABLE event_participants (
    event_id INT NOT NULL,
    member_id INT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('registered', 'attended', 'cancelled') DEFAULT 'registered',
    PRIMARY KEY (event_id, member_id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (member_id) REFERENCES members(id)
);

-- Products (Webshop)
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(100),
    image_url VARCHAR(500),
    stock_quantity INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Shopping Cart
CREATE TABLE carts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    status ENUM('active', 'checked_out', 'abandoned') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE cart_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cart_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Orders
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    status ENUM('pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    total_amount DECIMAL(10,2) NOT NULL,
    shipping_name VARCHAR(200),
    shipping_street VARCHAR(255),
    shipping_postal_code VARCHAR(10),
    shipping_city VARCHAR(100),
    stripe_payment_id VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Payments
CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT,
    order_id INT,
    amount DECIMAL(10,2) NOT NULL,
    payment_type ENUM('membership', 'order', 'event', 'other') NOT NULL,
    status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    stripe_payment_id VARCHAR(255),
    description VARCHAR(255),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- System Configuration
CREATE TABLE system_parameters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    param_key VARCHAR(100) UNIQUE NOT NULL,
    param_value TEXT,
    description VARCHAR(255),
    updated_by INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Audit Log
CREATE TABLE audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    details JSON,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 6. API Endpoint Structure (Python Backend)

### Authentication

```
POST   /api/auth/login              - Initiate login (email/passkey/Google)
POST   /api/auth/verify             - Verify email code
POST   /api/auth/refresh            - Refresh JWT token
POST   /api/auth/logout             - Invalidate session
GET    /api/auth/me                 - Get current user info
```

### Members

```
GET    /api/members                 - List members (filtered, paginated)
GET    /api/members/:id             - Get member by ID
GET    /api/members/me              - Get own profile
POST   /api/members                 - Create member
PUT    /api/members/:id             - Update member
PUT    /api/members/me              - Update own profile
DELETE /api/members/:id             - Delete member
GET    /api/members/export          - Export members (CSV/XLSX/PDF)
POST   /api/members/import          - Bulk import members
```

### Events

```
GET    /api/events                  - List events (filtered)
GET    /api/events/:id              - Get event by ID
POST   /api/events                  - Create event
PUT    /api/events/:id              - Update event
DELETE /api/events/:id              - Delete event
POST   /api/events/:id/register     - Register for event
GET    /api/events/:id/participants - List participants
GET    /api/events/analytics        - Event analytics
```

### Products

```
GET    /api/products                - List products (public catalog)
GET    /api/products/:id            - Get product by ID
POST   /api/products                - Create product (admin)
PUT    /api/products/:id            - Update product (admin)
DELETE /api/products/:id            - Delete product (admin)
POST   /api/products/:id/image      - Upload product image
```

### Cart & Orders

```
GET    /api/cart                     - Get current user's cart
POST   /api/cart/items              - Add item to cart
PUT    /api/cart/items/:id          - Update cart item quantity
DELETE /api/cart/items/:id          - Remove item from cart
DELETE /api/cart                     - Clear cart
POST   /api/orders                  - Create order (checkout)
GET    /api/orders                  - List user's orders
GET    /api/orders/:id              - Get order details
PUT    /api/orders/:id/status       - Update order status (admin)
```

### Payments

```
GET    /api/payments                - List payments
GET    /api/payments/:id            - Get payment by ID
POST   /api/payments                - Create payment record
GET    /api/payments/member/:id     - Get member's payments
POST   /api/payments/stripe/intent  - Create Stripe payment intent
POST   /api/payments/stripe/webhook - Stripe webhook handler
```

### Membership Types

```
GET    /api/memberships             - List membership types
GET    /api/memberships/:id         - Get membership type
POST   /api/memberships             - Create membership type
PUT    /api/memberships/:id         - Update membership type
DELETE /api/memberships/:id         - Delete membership type
```

### User Administration

```
GET    /api/admin/users             - List all users
GET    /api/admin/users/:id         - Get user details
POST   /api/admin/users             - Create user
PUT    /api/admin/users/:id         - Update user
DELETE /api/admin/users/:id         - Delete user
GET    /api/admin/roles             - List all roles
POST   /api/admin/users/:id/roles   - Assign role to user
DELETE /api/admin/users/:id/roles/:roleId - Remove role
```

### System

```
GET    /api/system/parameters       - Get system parameters
PUT    /api/system/parameters       - Update parameters
GET    /api/system/audit-log        - Get audit log
GET    /api/system/health           - Health check
```

---

## 7. Key Business Workflows

### 7.1 Member Registration Flow

```
[New User] → [Login/Register] → [Application Form (3 steps)]
     → [Submit] → [Status: verzoek_lid]
     → [Admin Reviews] → [Approve/Reject]
     → [If Approved] → [Role: hdcnLeden] → [Dashboard Access]
```

### 7.2 E-Commerce Flow

```
[Member] → [Browse Products] → [Add to Cart]
     → [View Cart] → [Checkout]
     → [Shipping Info] → [Stripe Payment]
     → [Order Confirmed] → [Email Notification]
     → [Admin: Update Status] → [Shipped] → [Delivered]
```

### 7.3 Regional Access Flow

```
[Admin Login] → [Check Permission Role] + [Check Region Role]
     → [Members_CRUD + Regio_Utrecht]
     → [Can ONLY see/edit Utrecht members]
     → [Data filtered server-side by region]
```

---

## 8. Non-Functional Requirements

| Requirement     | Target                                   |
| --------------- | ---------------------------------------- |
| Language        | Dutch (UI), English (code)               |
| Responsive      | Mobile-first, min 320px                  |
| Performance     | API response < 500ms                     |
| Availability    | 99.5% uptime                             |
| Security        | OWASP Top 10 compliance                  |
| Data Privacy    | GDPR/AVG compliant                       |
| Browser Support | Chrome, Firefox, Safari, Edge (latest 2) |
| Accessibility   | WCAG 2.1 AA                              |
| Max Users       | ~1100 members, ~10 concurrent admins      |

---

## 9. Migration Considerations (DynamoDB → MySQL)

| Current (DynamoDB)  | Target (MySQL)                 | Notes                                |
| ------------------- | ------------------------------ | ------------------------------------ |
| Single-table design | Normalized relational schema   | Better for complex queries           |
| Cognito auth        | JWT + OAuth 2.0 (self-managed) | More control, less vendor lock-in    |
| Lambda functions    | Python API server (FastAPI)    | Simpler deployment, lower cold-start |
| S3 file storage     | S3-compatible (keep or MinIO)  | No change needed                     |
| SAM/CloudFormation  | Docker + standard deploy       | Platform-agnostic                    |

---

## 10. Summary of Functional Scope

| Domain              | Screens | API Endpoints | Priority      |
| ------------------- | ------- | ------------- | ------------- |
| Authentication      | 3       | 5             | P0 - Critical |
| Dashboard           | 1       | 1             | P0 - Critical |
| Member Management   | 3       | 10            | P0 - Critical |
| My Account/Profile  | 2       | 3             | P0 - Critical |
| Webshop             | 4       | 9             | P1 - High     |
| Event Management    | 3       | 8             | P1 - High     |
| Payment Processing  | 2       | 6             | P1 - High     |
| Product Management  | 2       | 5             | P2 - Medium   |
| Membership Types    | 1       | 5             | P2 - Medium   |
| User Administration | 2       | 7             | P2 - Medium   |
| Advanced Exports    | 1       | 3             | P3 - Low      |
| System Config       | 1       | 3             | P3 - Low      |
| **TOTAL**           | **~25** | **~65**       |               |
