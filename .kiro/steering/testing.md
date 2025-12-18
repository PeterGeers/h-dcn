---
inclusion: manual
---

# H-DCN Dashboard Testing Guidelines

## Testing Strategy

### Frontend Testing (React TypeScript)

- Unit Tests: Jest for component logic and utilities
- Integration Tests: React Testing Library for user interactions
- E2E Tests: Custom test suite in frontend/test-e2e.js
- Property-Based Tests: Use fast-check for complex business logic

### Backend Testing (Python Lambda)

- Unit Tests: pytest for individual function ting
- Integration Tests: Mock AWS services with moto
- API Tests: Test API Gateway integration
- Property-Based Tests: Use Hypothesis for data validation

## Test Organization

### Frontend Ture

- Components: src/components/\__tes_/
- Modules: src/modules/{feature}/\__te_/
- Utils: src/utils/**tests**/

### Backend Test Structur

ts/unit/

- Integration: b/
- Fixtures: backend/tests/fixtures/

## Tes

### Frontend

- Co-locate te
- Mock external dependencies (API calls, AWS
- Test udetails
  vior

nd

- Test each Lambda handler inde
- Mock DynamoDB and other AWS services
- Validate input/output schemas
- Test error conditions and casesedge
