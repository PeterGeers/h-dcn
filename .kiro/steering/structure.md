---
inclusion: manual
---

# H-DCN Dashboard Project Structure

## Root Level Organization

```
h-dcn/
├── frontend/           # React TypeScript application
├── backend/            # AWS SAM serverless backend
├── git/                # Git automation scripts
├── scripts/            # Deployment and utility scripts
├── Prompts/            # Documentation and requirements
├── startUpload/        # S3 deployment utilities
├── .OLDvsc/            # Backup of old VS Code configuration (temporary)
├── .venv/              # Python virtual environment (local development)
├── .kiro/              # Kiro IDE configuration
│   ├── settings/       # MCP and workspace settings
│   ├── steering/       # Project guidelines
│   └── specs/          # Feature specifications
├── .gitguardian.yaml   # Security scanning configuration
└── README.md           # Project documentation
```

## Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   │   ├── common/     # Shared components (FunctionGuard, Guards, Selects)
│   │   ├── layout/     # Layout components (Header, Sidebar, etc.) - ready for implementation
│   │   └── __tests__/  # Component unit tests - ready for implementation
│   ├── modules/        # Feature-based modules
│   │   ├── members/    # Member management
│   │   │   ├── components/  # Member-specific components
│   │   │   ├── services/    # API calls and business logic
│   │   │   ├── types/       # TypeScript interfaces (member.types.ts)
│   │   │   └── __tests__/   # Module tests - ready for implementation
│   │   ├── events/     # Event management
│   │   │   └── __tests__/   # Event tests - ready for implementation
│   │   ├── webshop/    # E-commerce functionality
│   │   │   └── __tests__/   # Webshop tests - ready for implementation
│   │   └── products/   # Product management
│   │       └── __tests__/   # Product tests - ready for implementation
│   ├── config/         # Configuration files
│   ├── utils/          # Shared utilities and helpers
│   │   ├── api.ts      # API client configuration
│   │   └── __tests__/  # Utility tests - ready for implementation
│   ├── types/          # Global TypeScript type definitions (user.ts)
│   ├── hooks/          # Custom React hooks (useAuth.ts)
│   ├── context/        # React Context providers (AuthContext.tsx)
│   ├── assets/         # Static assets (images, fonts, etc.) - ready for use
│   ├── pages/          # Main application pages
│   └── App.tsx         # Main application component
├── public/             # Static public assets
├── build/              # Production build output
├── test/               # E2E and integration tests
├── package.json        # Dependencies and scripts
├── tsconfig.json       # TypeScript configuration
├── webpack.config.js   # Webpack optimization
└── .env                # Environment variables
```

## Backend Structure (`backend/`)

```
backend/
├── handler/            # Lambda function handlers (41 functions)
│   ├── create_*/       # Create operations
│   │   ├── app.py      # Lambda handler
│   │   ├── requirements.txt # Dependencies
│   │   └── __init__.py # Python package marker
│   ├── get_*/          # Read operations
│   ├── update_*/       # Update operations
│   ├── delete_*/       # Delete operations
│   └── hdcn_cognito_admin/ # Cognito user management
├── tests/              # Backend tests - organized structure
│   ├── unit/           # Unit tests - ready for implementation
│   ├── integration/    # Integration tests - ready for implementation
│   ├── fixtures/       # Test data and mocks (member_data.py)
│   └── conftest.py     # pytest configuration
├── Migratie/           # Migration tools and scripts
├── scripts/            # Utility scripts
├── events/             # Event definitions for SAM
├── template.yaml       # SAM infrastructure template
├── samconfig.toml      # SAM deployment configuration
└── requirements.txt    # Global Python dependencies
```

## Module Organization Patterns

### Frontend Module Structure

Each feature module follows this consistent pattern:

```
src/modules/{feature}/
├── components/         # Feature-specific components
│   ├── {Feature}Card.tsx
│   ├── {Feature}Form.tsx
│   ├── {Feature}List.tsx
│   └── __tests__/      # Component tests
├── services/           # API and business logic
│   ├── {feature}Api.ts # API calls
│   ├── {feature}Service.ts # Business logic
│   └── __tests__/      # Service tests
├── types/              # TypeScript interfaces
│   └── {feature}.types.ts
├── hooks/              # Feature-specific hooks
│   └── use{Feature}.ts
└── pages/              # Main feature pages
    ├── {Feature}List.tsx
    ├── {Feature}Detail.tsx
    └── {Feature}Edit.tsx
```

### Backend Handler Structure

Each Lambda function follows this pattern:

```
backend/handler/{operation}_{entity}/
├── app.py              # Main Lambda handler
├── requirements.txt    # Function-specific dependencies
├── __init__.py         # Python package marker
└── test_app.py         # Co-located unit tests (optional)
```

## Key Conventions

### File Naming

**Frontend:**

- **Components**: PascalCase (`MemberCard.tsx`)
- **Files**: kebab-case for utilities (`api-service.ts`)
- **Directories**: kebab-case (`src/modules/member-management/`)
- **Props/Variables**: camelCase (`memberData`, `isLoading`)

**Backend:**

- **Lambda Functions**: snake_case (`create_member`, `get_events`)
- **DynamoDB Tables**: PascalCase (`Members`, `Events`, `Products`)
- **API Endpoints**: RESTful with entity collections (`/members`, `/events/{id}`)

### Import Patterns

**Frontend:**

- **Absolute imports**: From `src/` root for cross-module imports
- **Relative imports**: For same-module components
- **Lazy loading**: Component-level code splitting for performance

**Backend:**

- **Local imports**: Within handler directory
- **Shared utilities**: Common functions in separate modules

## Configuration Management

### Frontend Configuration

- **Environment variables**: In `.env` files
- **Build configuration**: `webpack.config.js` for optimization
- **TypeScript**: Strict mode configuration in `tsconfig.json`

### Backend Configuration

- **Infrastructure**: SAM template parameters
- **Dynamic config**: AWS Systems Manager Parameter Store
- **Environment**: Lambda environment variables

## API Structure

### RESTful URLs

- **Entity collections**: `/members`, `/events`, `/products`
- **Specific entities**: `/members/{id}`, `/events/{id}`
- **Nested resources**: `/members/{id}/groups`

### CRUD Operations

- **Create**: POST `/entities`
- **Read**: GET `/entities` (list), GET `/entities/{id}` (single)
- **Update**: PUT `/entities/{id}`
- **Delete**: DELETE `/entities/{id}`

### Entity-based Grouping

- **Members**: User management and profiles
- **Events**: Club events and participation
- **Products**: E-commerce catalog and orders
- **Admin**: System administration and configuration

## Performance Optimization

### Frontend

- **Lazy loading**: Component-level code splitting
- **Bundle optimization**: Webpack configuration for smaller bundles
- **Caching**: API response caching and local storage

### Backend

- **Cold start optimization**: Minimal initialization code
- **Connection pooling**: Reuse database connections
- **Caching**: DynamoDB query result caching

## Security Patterns

### Frontend

- **Authentication**: AWS Cognito integration
- **Authorization**: Role-based component rendering
- **Input validation**: Client-side validation with server-side verification

### Backend

- **Authentication**: JWT token validation
- **Authorization**: Function-level permissions via Parameter Store
- **Input sanitization**: All API inputs validated and sanitized

## Development Workflow

### Local Development

1. **Frontend**: `npm start` for development server
2. **Backend**: `sam local start-api` for local API testing
3. **Testing**: Separate test commands for frontend and backend

### Deployment

1. **Frontend**: Build and deploy to S3 with CloudFront
2. **Backend**: SAM CLI deployment to AWS Lambda
3. **Infrastructure**: CloudFormation stack management via SAM
