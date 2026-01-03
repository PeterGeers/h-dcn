# H-DCN Portal Technical Guidelines

This document outlines the technical architecture, conventions, and development guidelines for the H-DCN portal project.

## Technology Stack

### Frontend (React TypeScript)

- **Framework**: React 18 with TypeScript
- **UI Library**: Chakra UI - component library with theme support
- **Routing**: React Router v6 - client-side routing
- **Forms**: Formik + Yup - form handling and validation
- **State Management**: React Context API - avoid prop drilling
- **HTTP Client**: Custom fetch utilities in `src/utils/api.ts`
- **Payments**: Stripe React integration
- **Build**: Create React App (CRA)

#### Look and Feel Guidelines

See detailed design system guidelines in: **[Look and Feel Guidelines](.kiro/specs/steering/look-and-feel.md)**

**Quick Reference:**

- **Primary Brand Color**: H-DCN Orange `#f56500`
- **Field States**: Visual cues (colors, cursors, backgrounds) instead of text badges
- **Dark Theme**: Gray.800/Gray.700 backgrounds with orange accents
- **Icons**: Consistent Chakra UI icons with semantic colors (ViewIcon=blue, EditIcon=orange, DeleteIcon=red)
- **Responsive**: Mobile-first design with `{{ base: 'sm', md: 'md' }}` patterns
- **Accessibility**: WCAG AA compliance with proper ARIA labels
- **Cards**: Orange headings, fixed modal positioning, proper spacing
- **Tables**: Dark theme with orange headers, sticky actions, responsive hiding

### Backend (Python Serverless)

- **Runtime**: Python 3.11 with AWS Lambda
- **Database**: DynamoDB (NoSQL) - use consistent partition/sort key patterns
- **Infrastructure**: AWS SAM - all resources defined in `template.yaml`
- **Configuration**: AWS Systems Manager Parameter Store for dynamic config
- **Region**: eu-west-1 (Ireland) - hardcoded in all AWS resources

## Code Conventions

### Frontend Naming

- **Components**: PascalCase (`MemberCard.tsx`)
- **Files**: kebab-case for utilities (`api-service.ts`)
- **Directories**: kebab-case (`src/modules/member-management/`)
- **Props/Variables**: camelCase (`memberData`, `isLoading`)

### Backend Naming

- **Lambda Functions**: snake_case (`create_member`, `get_events`)
- **DynamoDB Tables**: PascalCase (`Members`, `Events`, `Products`)
- **API Endpoints**: RESTful with entity collections (`/members`, `/events/{id}`)

### File Organization

- **Frontend Modules**: Feature-based in `src/modules/{feature}/`
- **Shared Components**: `src/components/` for reusable UI
- **Backend Handlers**: `backend/handler/{operation}_{entity}/app.py`
- **Each Lambda**: Separate directory with `app.py`, `requirements.txt`, `__init__.py`

## Architecture Patterns

### API Design

- **RESTful**: Standard HTTP methods (GET, POST, PUT, DELETE)
- **Response Format**: Consistent JSON with `statusCode`, `body`, `headers`
- **Error Handling**: HTTP status codes with descriptive error messages
- **CORS**: Enabled on all endpoints for cross-origin requests

### Data Patterns

- **Primary Keys**: UUID v4 for all entities
- **Timestamps**: ISO 8601 format (`2024-01-01T12:00:00Z`)
- **Soft Deletes**: Use `deleted_at` timestamp instead of hard deletes
- **Pagination**: Use `limit` and `last_evaluated_key` for DynamoDB scans

### Security Patterns

- **Authentication**: AWS Cognito User Pools with JWT tokens
- **Authorization**: Function-level permissions via Parameter Store
- **Regional Access**: Role-based access control (`hdcnRegio_*` groups)
- **Input Validation**: Server-side validation for all API inputs

## Development Guidelines

### Frontend Development

- Use TypeScript strict mode - no `any` types
- Implement proper error boundaries and loading states
- Follow Chakra UI responsive design patterns
- Use React Context for global state, local state for component-specific data
- Implement proper form validation with Formik + Yup

### Backend Development

- Each Lambda function should be single-purpose and stateless
- Use proper exception handling with try/catch blocks
- Log important events for CloudWatch monitoring
- Validate all inputs before processing
- Use environment variables for configuration

### Testing Requirements

- **Frontend**: Jest for unit tests, focus on business logic
- **Backend**: pytest for unit tests, mock AWS services
- **Integration**: API Gateway integration tests in `backend/tests/integration/`

### Deployment Process

- Use PowerShell scripts for automated deployment
- Frontend deploys to S3 with CloudFront distribution
- Backend deploys via SAM CLI with guided configuration
- Environment-specific configurations in `.env` and SAM parameters

## Key Business Rules

- **Member Access**: Regional admins can only access their region's members
- **Function Permissions**: Dynamic permissions loaded from Parameter Store
- **Payment Processing**: Stripe integration with order tracking
- **File Uploads**: S3 with proper content-type handling for images

## Performance Guidelines

- **Frontend**: Lazy loading, code splitting, memoization
- **Backend**: DynamoDB query optimization, Lambda cold start reduction
- **Caching**: CloudFront for static assets, API Gateway caching for dynamic content
- **Monitoring**: CloudWatch metrics and alarms for performance tracking

## Security Best Practices

- **Data Protection**: Encrypt sensitive data at rest and in transit
- **Access Control**: Principle of least privilege for all roles
- **Input Sanitization**: Validate and sanitize all user inputs
- **Audit Logging**: Log all significant user actions and system events
