# Implementation Plan: Member Reporting Performance

> **⚠️ DEVELOPMENT SPECIFICATION**
>
> This implementation plan is for developing a NEW regional filtering system that will replace the existing S3 Parquet system in production.

## Related Documents

- **Requirements**: [Requirements.md](./Requirements.md) - Detailed requirements with acceptance criteria
- **Design**: [design.md](./design.md) - Complete system design with architecture, components, and interfaces

## Overview

This plan implements a simplified regional filtering system with backend filtering and browser session caching. The implementation will be done in a development environment first, then deployed to production, followed by removal of the old Parquet system.

## Tasks

- [x] 1. Set up backend regional filtering Lambda function
  - Create new Lambda handler directory structure
  - Implement JWT extraction and regional permission validation
  - Implement DynamoDB scan with Decimal conversion
  - Implement regional filtering logic (region-based only, no status filtering)
  - Add error handling and logging
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Write backend unit tests
  - [x] 2.1 Test `filter_members_by_region()` for Regio_All users
    - Verify all members from all regions are returned
    - _Requirements: 1.2_
  - [x] 2.2 Test `filter_members_by_region()` for regional users
    - Verify only members from user's region are returned
    - Verify all statuses are included (no status filtering)
    - _Requirements: 1.3_
  - [x] 2.3 Test `convert_dynamodb_to_python()` Decimal conversion
    - Verify Decimal integers convert to int
    - Verify Decimal floats convert to float
    - Verify nested objects are handled correctly
    - _Requirements: 1.5_
  - [x] 2.4 Test authentication and authorization
    - Test missing JWT token returns 401
    - Test invalid permissions return 403
    - Test valid permissions allow access
    - _Requirements: 1.1_

- [x] 3. Update SAM template for new Lambda function
  - Add `GetMembersFilteredFunction` resource
  - Configure API Gateway endpoint `GET /api/members`
  - Set up IAM permissions for DynamoDB read access
  - Configure environment variables (table name, region)
  - Add CORS configuration
  - _Requirements: 1.1, 1.4, 1.5_

- [x] 4. Deploy and test backend in development environment
  - Deploy Lambda function to development
  - Test with Postman/curl using real JWT tokens
  - Verify regional filtering works correctly
  - Verify response times meet <1 second requirement
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 5. Checkpoint - Backend validation
  - Ensure all backend tests pass
  - Verify API endpoint works in development
  - Ask user if questions arise

- [x] 6. Implement frontend MemberDataService
  - Create `frontend/src/services/MemberDataService.ts`
  - Implement `fetchMembers()` with session storage caching
  - Implement `getCachedMembers()` for cache retrieval
  - Implement `cacheMembers()` for session storage
  - Implement `clearCache()` for manual refresh
  - Implement `refreshMembers()` for force refresh
  - Integrate with `computeCalculatedFieldsForArray()` from calculatedFields.ts
  - Add error handling for network and storage failures
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7. Write frontend service unit tests
  - [x] 7.1 Test `fetchMembers()` caches data in session storage
    - _Requirements: 2.1_
  - [x] 7.2 Test `fetchMembers()` uses cache on second call
    - _Requirements: 2.2_
  - [x] 7.3 Test `refreshMembers()` clears cache and fetches fresh
    - _Requirements: 3.2_
  - [x] 7.4 Test session storage unavailable fallback
    - _Requirements: 2.4_
  - [x] 7.5 Test calculated fields are computed after fetch
    - Verify korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar are added
    - _Requirements: 2.1_

- [x] 8. Implement MemberList component updates
  - Update `frontend/src/components/MemberList.tsx`
  - Integrate MemberDataService for data fetching
  - Add loading state and spinner
  - Add error state and error messages
  - Add "Refresh Data" button for CRUD users (check permissions)
  - Implement `handleRefresh()` with loading indicator
  - Display member count (filtered / total)
  - Preserve UI state during refresh (filters, scroll position)
  - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 6.1, 6.2, 6.3_

- [x] 9. Implement or update MemberFilters component
  - Create/update `frontend/src/components/MemberFilters.tsx`
  - Add filter controls for: status, region, membership type, search text, birthday month
  - Implement `applyFilters()` function with AND logic
  - Update filtered results within 200ms
  - Maintain filter state during navigation
  - Display filtered count and total count
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Write frontend component unit tests
  - [x] 10.1 Test MemberList loads and displays data
    - _Requirements: 2.1, 6.1_
  - [x] 10.2 Test MemberList shows loading indicator
    - _Requirements: 6.3_
  - [x] 10.3 Test MemberList shows error messages
    - _Requirements: 6.1, 6.2_
  - [x] 10.4 Test refresh button only shows for CRUD users
    - _Requirements: 3.1_
  - [x] 10.5 Test refresh button clears cache and fetches fresh data
    - _Requirements: 3.2, 3.4_
  - [x] 10.6 Test filter controls update results
    - _Requirements: 5.1, 5.2_
  - [x] 10.7 Test multiple filters combine with AND logic
    - _Requirements: 5.3_

- [x] 11. Integration testing in development environment
  - Test complete user flow: load → filter → refresh
  - Test with different user roles (regional users, Regio_All, CRUD users)
  - Verify session storage caching works across page navigation
  - Test performance (load times, filter response times)
  - Test error scenarios (network failure, invalid JWT, DynamoDB errors)
  - _Requirements: All_

- [ ] 12. Checkpoint - Development validation
  - Ensure all tests pass
  - Verify performance meets requirements (<2s load, <200ms filter)
  - Get user acceptance in development environment
  - Ask user if questions arise

- [ ] 13. Deploy to production
  - Deploy backend Lambda function to production
  - Deploy frontend to production
  - Monitor CloudWatch logs for errors
  - Monitor performance metrics
  - Gather initial user feedback
  - _Requirements: All_

- [ ] 14. Production validation checkpoint
  - Verify new system works correctly in production
  - Confirm no critical issues
  - Get user sign-off before removing old system
  - Ask user if questions arise

- [x] 15. Remove old Parquet system from production
  - [x] 15.1 Remove Parquet Lambda functions
    - Delete `backend/handler/generate_member_parquet/` directory
    - Delete `backend/handler/download_parquet/` directory
    - _Requirements: 4.1, 4.2_
  - [x] 15.2 Update SAM template
    - Remove `GenerateMemberParquetFunction` resource
    - Remove `DownloadParquetFunction` resource
    - Remove Parquet API Gateway endpoints
    - Remove associated IAM roles and policies
    - _Requirements: 4.5, 4.6_
  - [x] 15.3 Clean up S3 storage
    - Delete `s3://my-hdcn-bucket/analytics/parquet/members/` prefix and files
    - _Requirements: 4.4_
  - [x] 15.4 Remove Parquet frontend code
    - Remove Parquet UI buttons from member reporting page
    - Delete `ParquetDataService.ts` if it exists
    - Delete `useParquetData.ts` hook if it exists
    - Remove any Parquet-related imports and references
    - _Requirements: 4.3_
  - [x] 15.5 Deploy cleanup changes
    - Deploy updated SAM template (removes Parquet functions)
    - Deploy updated frontend (removes Parquet UI)
    - Verify no errors in production

- [ ] 16. Final validation and documentation
  - Verify all Parquet code and resources are removed
  - Update system documentation
  - Document new regional filtering API
  - Create user guide for refresh button
  - Archive this spec as completed

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and user feedback
- Backend development and testing happens before frontend work
- Development environment validation before production deployment
- Old Parquet system removal only after new system is validated in production
- All tests should pass before proceeding to next phase
