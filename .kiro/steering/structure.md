# Project Structure

```
h-dcn/
├── backend/                    # AWS SAM serverless backend
│   ├── template.yaml           # SAM/CloudFormation template (all resources defined here)
│   ├── handler/                # Lambda function handlers (one folder per function)
│   │   ├── <function_name>/
│   │   │   ├── app.py          # Lambda entry point (lambda_handler)
│   │   │   └── requirements.txt # Per-function dependencies (if any)
│   │   └── ...
│   ├── layers/
│   │   └── auth-layer/         # Shared Lambda Layer
│   │       └── python/shared/
│   │           ├── auth_utils.py          # Auth, CORS, permission validation
│   │           └── maintenance_fallback.py # Graceful fallback when layer unavailable
│   ├── tests/
│   │   ├── unit/               # Unit tests (pytest + moto)
│   │   ├── integration/        # Integration tests
│   │   ├── fixtures/           # Test fixtures
│   │   └── conftest.py         # Shared pytest fixtures
│   ├── email-templates/        # SES email template configs
│   └── requirements.txt        # Root backend dependencies
│
├── frontend/                   # React SPA (TypeScript)
│   ├── src/
│   │   ├── pages/              # Top-level route pages
│   │   ├── modules/            # Feature modules (members, events, products, webshop, advanced-exports)
│   │   ├── components/         # Shared UI components
│   │   ├── services/           # API and business logic services
│   │   ├── hooks/              # Custom React hooks
│   │   ├── context/            # React context providers
│   │   ├── config/             # App configuration
│   │   ├── types/              # TypeScript type definitions
│   │   ├── utils/              # Utility functions
│   │   └── assets/             # Static assets
│   ├── public/                 # Static public files
│   ├── package.json            # Dependencies and scripts
│   ├── tsconfig.json           # TypeScript config
│   └── webpack.config.js       # Webpack overrides
│
├── infrastructure/             # IaC templates (IAM roles, budgets, CloudTrail)
├── .github/workflows/          # CI/CD pipelines
├── scripts/                    # Utility/migration scripts
└── docs/                       # Documentation
```

## Conventions

### Backend Handler Pattern

Each Lambda function lives in `backend/handler/<function_name>/app.py` and follows this structure:

1. Import from `shared.auth_utils` (with fallback to `maintenance_fallback`)
2. Initialize DynamoDB resource/table
3. Export `lambda_handler(event, context)` function
4. Use `extract_user_credentials()` → `validate_permissions_with_regions()` for auth
5. Use `create_success_response()` / `create_error_response()` for responses
6. All responses include CORS headers via the shared layer

### Frontend Module Pattern

Feature code is organized under `frontend/src/modules/<feature>/` for domain-specific components and logic. Shared services live in `frontend/src/services/`.

### Naming

- Backend handler folders: snake_case (e.g., `get_members`, `create_order`)
- Frontend files: PascalCase for components, camelCase for services and utilities
- DynamoDB tables: PascalCase (e.g., `Members`, `Payments`)
