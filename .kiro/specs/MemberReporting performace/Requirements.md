# Requirements Document: Member Reporting Performance

## Introduction

This document specifies requirements for improving the performance of member reporting and analysis functionality. The system currently experiences performance issues when loading and filtering large member datasets.

Two architectural approaches are being evaluated:

1. **S3 Parquet Approach** (currently implemented)
2. **Backend Cache with Regional Filtering** (proposed alternative)

This document analyzes both approaches and specifies requirements for the optimal solution.

## Architectural Analysis

### Approach 1: S3 Parquet File (Current Implementation)

**How it works:**

- User with Members_CRUD permission generates a Parquet file from DynamoDB
- File is stored in S3 at `analytics/parquet/members/`
- Any user with member permissions downloads the full Parquet file to browser
- Frontend performs all filtering (region, status, membership type)
- No caching - file is downloaded fresh each time

**Positives:**

- ✅ **Offline Analysis**: Users can download and analyze data offline
- ✅ **No Backend Load**: Filtering happens in browser, reducing backend compute
- ✅ **Efficient Format**: Parquet is highly compressed and optimized for analytics
- ✅ **Simple Architecture**: No cache invalidation logic needed
- ✅ **Audit Trail**: S3 provides built-in versioning and access logs
- ✅ **Already Implemented**: Code exists and is working

**Negatives:**

- ❌ **Large Downloads**: Users download ALL member data (1500+ members) every time
- ❌ **Slow Initial Load**: 5-10 second wait for large file download
- ❌ **Bandwidth Waste**: Regional users download data they can't access
- ❌ **No Caching**: Repeated visits require full re-download
- ❌ **Browser Memory**: Large dataset loaded into browser memory
- ❌ **Security Concern**: All data exposed to browser (even if filtered in UI)

**Performance Metrics (estimated for 1500 members):**

- File size: ~500KB-1MB compressed Parquet
- Download time: 2-5 seconds (depending on connection)
- Browser processing: 1-2 seconds
- Total time to interactive: 3-7 seconds
- Bandwidth per session: 500KB-1MB

---

### Approach 2: Backend Regional Filtering (Simplified - Proposed)

**How it works:**

- Backend extracts regional parameters from JWT token
- Backend filters member data by region BEFORE sending to frontend
- Frontend receives only relevant data for user's region
- Frontend caches data in browser session storage (automatic, no backend complexity)
- CRUD users get a refresh button to fetch latest data

**Positives:**

- ✅ **Smaller Payloads**: Regional users only receive their region's data (100-200 members vs 1500)
- ✅ **Faster Loads**: 70-90% reduction in data transfer for regional users
- ✅ **Better Security**: Users never receive data outside their permissions
- ✅ **Less Browser Memory**: Smaller datasets in browser
- ✅ **Simple Architecture**: No backend cache management needed
- ✅ **Always Fresh**: Each session gets current data from DynamoDB
- ✅ **Browser Caching**: Browser automatically caches during session (free)

**Negatives:**

- ❌ **Backend Compute**: Filtering logic runs on every request (but DynamoDB scan is fast for 1500 members)
- ❌ **Implementation Work**: Requires new regional filtering endpoint

**Note on Caching:**
Given that users login briefly and infrequently (few times per month), complex backend caching with TTL is unnecessary. Browser session storage provides automatic caching during the user's session, and each new session gets fresh data.

**Note on Offline Analysis:**
Frontend already has CSV/XLSX export features, so users CAN download and analyze their permitted data offline. Regional users get their region's data, administrators with Regio_All get all data.
All current reporting and analysis functions should now use the memory cache

**Performance Metrics (estimated for regional user with 200 members):**

- Payload size: ~100-150KB JSON
- Download time: 0.5-1 second
- DynamoDB scan time: ~200-500ms (for 1500 members)
- Total time to interactive: 1-2 seconds
- Bandwidth per session: 100-150KB
- Subsequent page loads: Instant (browser session storage)

---

## Recommendation: Simplified Regional Filtering (Final Decision)

**Chosen approach:**

1. **Add backend regional filtering API** - filters data by user's region before sending
2. **Use browser session storage** - automatic caching during user's session (no backend complexity)
3. **Remove S3 Parquet system** - eliminate unnecessary complexity
4. **Keep frontend CSV/XLSX export** - continues to work for offline analysis

**Why This Works:**

- ✅ **Simple**: No backend cache management, no Parquet generation, no S3 storage
- ✅ **Fast**: Regional users get 70-90% smaller payloads (200 vs 1500 members)
- ✅ **Secure**: Users only receive data they're permitted to see
- ✅ **Fresh**: Each session gets current data from DynamoDB
- ✅ **Fits Usage Pattern**: Short, infrequent sessions don't benefit from complex caching
- ✅ **Browser Handles Caching**: Session storage provides free caching during user's session
- ✅ **Less Code**: Remove Parquet handlers, reduce maintenance burden
- ✅ **Offline Analysis**: Frontend CSV/XLSX export handles this use case

**What Changes:**

- **Remove**: S3 Parquet generation and download handlers
- **Remove**: Parquet-related UI buttons and API endpoints
- **Add**: New regional filtering API endpoint
- **Add**: Application refresh button for CRUD users
- **Keep**: Frontend CSV/XLSX export (already exists)
- **Result**: Simpler architecture, 70-90% faster loads for regional users

---

## Glossary

- **Member_Reporting_System**: The application component responsible for displaying and analyzing member data
- **Parquet_Generator**: The backend service that creates Parquet files from the member table
- **Cache_Manager**: The component responsible for managing cached member data with TTL
- **Regional_Filter**: A filter that restricts member data based on regional parameters (Regio_All or Regio_xxxx)
- **JWT_Token**: JSON Web Token containing user credentials and regional parameters
- **CRUD_User**: A user with Create, Read, Update, Delete permissions for member data
- **Session_Storage**: Browser-based storage that persists data for the duration of a user's session

---

## Requirements: Simplified Regional Filtering

### Requirement 1: Backend Regional Data API

**User Story:** As a regional user, I want to receive only active member data for my region, so that I can work with a smaller, faster dataset of relevant members.

**Design Note:** Regional users (Regio_Utrecht, Regio_Zuid-Holland, etc.) only receive members with active statuses to focus on current members. Regio_All users receive all members including historical records for comprehensive reporting.

**Implementation Note:** The status field enumOptions in `frontend/src/config/memberFields.ts` defines all possible status values. The backend filtering logic uses a subset of these values for regional users.

#### Acceptance Criteria

1. WHEN a user requests member data, THE system SHALL extract regional parameters from the JWT_Token
2. WHERE the JWT_Token contains Regio_All permission, THE system SHALL return all member data regardless of status
3. WHERE the JWT_Token contains a specific Regio_xxxx parameter, THE system SHALL return only members from that region with status "Actief", "Opgezegd", "wachtRegio", "Aangemeld", or "Geschorst"
4. WHEN regional filtering is applied, THE system SHALL complete the filter operation within 1 second
5. THE system SHALL return data in JSON format optimized for frontend consumption

### Requirement 2: Frontend Session Caching

**User Story:** As a user, I want member data to be cached in my browser session, so that navigating within the reporting interface is instant.

#### Acceptance Criteria

1. WHEN member data is received from the backend, THE Member_Reporting_System SHALL store it in browser session storage
2. WHEN a user navigates within the reporting interface, THE system SHALL use cached data from session storage
3. WHEN the browser session ends, THE system SHALL automatically clear the cached data
4. WHEN session storage is unavailable, THE system SHALL function normally without caching
5. THE system SHALL cache data separately for each user to prevent data leakage in shared browser environments

### Requirement 3: Manual Data Refresh

**User Story:** As a CRUD user, I want to manually refresh member data with an application button, so that I can see the latest updates immediately after making changes without losing my current UI state.

**Design Note:** This is an application-level refresh button (not browser F5 refresh) because:

- Preserves UI state (filters, scroll position, current page)
- Provides clear user feedback (loading indicator, success message)
- More intuitive than browser refresh for seeing data changes
- Professional user experience

#### Acceptance Criteria

1. WHERE a user has members_update or members_create permissions, THE Member_Reporting_System SHALL display a "Refresh Data" button in the member reporting interface
2. WHEN a CRUD_User clicks the refresh button, THE system SHALL clear session storage and fetch fresh data from the backend
3. WHILE the refresh operation is in progress, THE system SHALL display a loading indicator and disable the refresh button
4. WHEN the refresh operation completes, THE Member_Reporting_System SHALL update the displayed data, preserve UI state (filters, scroll position), and show a success notification
5. WHEN the refresh operation fails, THE Member_Reporting_System SHALL display an error message and retain the existing cached data
6. THE system SHALL log all manual refresh operations for audit purposes

### Requirement 4: Remove Parquet Export System

**User Story:** As a system maintainer, I want to remove the S3 Parquet export system, so that we have a simpler architecture with less code to maintain.

**Rationale:** The regional filtering API provides better performance and security. The Parquet system adds unnecessary complexity since:

- Frontend already has CSV/XLSX export for offline analysis
- Regional filtering is faster and more secure
- Parquet generation/download handlers are no longer needed

#### Acceptance Criteria

1. THE system SHALL remove the Parquet generation Lambda function (generate_member_parquet)
2. THE system SHALL remove the Parquet download Lambda function (download_parquet)
3. THE system SHALL remove any UI buttons or links related to Parquet export
4. THE system SHALL remove the S3 bucket prefix `analytics/parquet/members/` and any existing Parquet files
5. THE system SHALL update API Gateway to remove Parquet-related endpoints
6. THE system SHALL remove any CloudFormation/SAM template resources related to Parquet generation

### Requirement 5: Frontend Data Filtering

**User Story:** As a user, I want to filter member data in the browser by any column, so that I can quickly find specific members without additional server requests.

#### Acceptance Criteria

1. WHEN member data is loaded, THE Member_Reporting_System SHALL enable filtering by all member columns including status, membership type, region, birthday, name, email, phone, address, and any other member attributes
2. WHEN a user applies a filter, THE Member_Reporting_System SHALL update the displayed results within 200ms
3. WHEN multiple filters are applied, THE Member_Reporting_System SHALL combine them using AND logic
4. THE Member_Reporting_System SHALL maintain filter state when the user navigates within the reporting interface
5. THE system SHALL display the count of filtered results and total records

### Requirement 6: Basic Error Handling

**User Story:** As a user, I want to see clear error messages when data loading fails, so that I understand what went wrong.

#### Acceptance Criteria

1. WHEN the backend API fails to load member data, THE system SHALL display a user-friendly error message
2. WHEN an error occurs, THE system SHALL log the error details for troubleshooting
3. WHEN data loading is in progress, THE system SHALL display a loading indicator
