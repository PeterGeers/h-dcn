# Implementation Plan: PresMeet Club Logo Upload

## Overview

This implementation adds a clickable club logo upload feature to the PresMeet booking page. The backend receives a base64-encoded image, resizes it to 200×200 pixels using Pillow, stores it as PNG in the frontend S3 bucket, and returns a cache-busted URL. The frontend renders the logo (or placeholder), handles file selection/validation, and updates the display on success.

## Tasks

- [x] 1. Backend: Create upload_club_logo Lambda handler
  - [x] 1.1 Create handler directory and implement app.py
    - Create `backend/handler/upload_club_logo/app.py`
    - Import from `shared.auth_utils` with maintenance fallback
    - Implement `lambda_handler(event, context)` with full request lifecycle:
      - Extract and validate auth credentials via `extract_user_credentials()`
      - Parse request body for `image_data`, `club_id`, `content_type` fields
      - Return 400 if any required field is missing
      - Look up user's club_id from Members table using authenticated email
      - Authorize: allow if request club_id matches user's club_id, OR user has `Products_CRUD` or `Webshop_Management` role; otherwise return 403
      - Validate content_type is one of: `image/png`, `image/jpeg`, `image/webp`, `image/gif`
      - Decode base64 image_data; return 400 if decoding fails
      - Validate decoded size ≤ 5MB (5,242,880 bytes); return 413 if exceeded
      - Open image with Pillow; return 400 if not a valid image
      - Resize to fit within 200×200 bounding box preserving aspect ratio
      - Convert to PNG format
      - Upload to S3 at `assets/presmeet/logos/{club_id}.png` with `ContentType: image/png` and `CacheControl: max-age=0, must-revalidate`
      - Return 200 with `logo_url` including `?t={unix_timestamp}` cache-buster
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1_

  - [x] 1.2 Create requirements.txt for Pillow dependency
    - Create `backend/handler/upload_club_logo/requirements.txt` with `Pillow` dependency
    - _Requirements: 4.1_

  - [x] 1.3 Add UploadClubLogoFunction to SAM template
    - Add new `UploadClubLogoFunction` Lambda resource in `backend/template.yaml`
    - Configure API Gateway event: `POST /presmeet/logo`
    - Set environment variables: `MEMBERS_TABLE_NAME`, `FRONTEND_BUCKET_NAME`, `COGNITO_USER_POOL_ID`
    - Reference shared auth layer
    - Add IAM policy for `s3:PutObject` on `arn:aws:s3:::h-dcn-frontend-506221081911/assets/presmeet/logos/*`
    - _Requirements: 4.4, 5.1_

- [x] 2. Checkpoint - Backend handler complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Backend: Property-based and unit tests
  - [x] 3.1 Write property test for client-side file size validation boundary
    - **Property 1: Client-side file size validation boundary**
    - **Validates: Requirements 2.3**
    - Generate random integers around the 5MB boundary, verify accept/reject behavior

  - [x] 3.2 Write property test for base64 encoding round-trip
    - **Property 2: Base64 encoding round-trip**
    - **Validates: Requirements 3.1**
    - Generate random byte arrays, encode to base64, decode, assert equality

  - [x] 3.3 Write property test for image resize within 200×200
    - **Property 3: Image resize fits within 200×200 preserving aspect ratio**
    - **Validates: Requirements 4.1**
    - Generate random (width, height) pairs, create Pillow images, resize, verify output dimensions satisfy constraints

  - [x] 3.4 Write property test for invalid image data returning 400
    - **Property 4: Invalid image data produces 400 error without S3 side effects**
    - **Validates: Requirements 4.2, 4.7**
    - Generate random non-image byte sequences, invoke handler with mocked S3, verify 400 and no put_object call

  - [x] 3.5 Write property test for output always being valid PNG
    - **Property 5: Output is always valid PNG**
    - **Validates: Requirements 4.3**
    - Generate valid images in each supported format, process through resize, verify PNG magic bytes

  - [x] 3.6 Write property test for S3 key construction
    - **Property 6: S3 key construction matches pattern**
    - **Validates: Requirements 4.4**
    - Generate random club_id strings, verify constructed key equals `assets/presmeet/logos/{club_id}.png`

  - [x] 3.7 Write property test for server-side payload size limit
    - **Property 7: Server-side payload size limit**
    - **Validates: Requirements 4.8**
    - Generate oversized base64 payloads, invoke handler, verify 413 response

  - [x] 3.8 Write property test for authorization logic
    - **Property 8: Authorization — club ownership or admin override**
    - **Validates: Requirements 5.5, 5.6**
    - Generate (user_club_id, request_club_id, user_roles) tuples, verify access decision matches expected logic

  - [x] 3.9 Write property test for cache-busting URL format
    - **Property 9: Response URL contains cache-busting parameter**
    - **Validates: Requirements 6.1**
    - Generate random club_ids, invoke successful upload (mocked S3), verify URL contains expected pattern

  - [x] 3.10 Write unit tests for upload_club_logo handler
    - Test happy path: valid JPEG upload → resized PNG in S3, correct response
    - Test edge case: exactly 5MB file (accepted)
    - Test edge case: 5MB + 1 byte file (rejected with 413)
    - Test edge case: club_id with special characters
    - Test auth flow with mocked Cognito/DynamoDB
    - Test missing fields return 400
    - Test invalid content_type returns 400
    - Test user with no club_id returns 403
    - Test club_id mismatch (non-admin) returns 403
    - Test admin override allows any club_id
    - _Requirements: 4.1, 4.2, 4.7, 4.8, 5.2, 5.3, 5.5, 5.6_

- [x] 4. Checkpoint - Backend tests complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Frontend: Create ClubLogoUploader component
  - [x] 5.1 Create ClubLogoUploader React component
    - Create `frontend/src/modules/presmeet/components/ClubLogoUploader.tsx`
    - Implement `ClubLogoUploaderProps` interface with `clubId: string` and `isAdmin?: boolean`
    - Render 48×48 rounded image (or placeholder icon when no logo exists)
    - Add tooltip on hover indicating clickable for upload
    - Implement hidden `<input type="file" accept="image/png,image/jpeg,image/webp,image/gif">`
    - On click, trigger file selection dialog
    - Validate selected file size ≤ 5MB client-side; show Chakra UI toast if exceeded
    - Read selected file as base64 string
    - Show loading overlay during upload
    - On success, update image src with returned URL (including cache-bust param)
    - On error, show Chakra UI toast with error message and revert to previous image
    - On network failure, show toast suggesting retry
    - Persist cache-busting parameter in component state
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 6.2, 6.3, 7.1, 7.2, 7.3_

  - [x] 5.2 Add uploadClubLogo API function
    - Add `uploadClubLogo` method to `frontend/src/modules/presmeet/services/presmeetApi.ts`
    - Signature: `uploadClubLogo(imageData: string, clubId: string, contentType: string): Promise<ApiResponse<{ logo_url: string }>>`
    - POST to `/presmeet/logo` with `{ image_data, club_id, content_type }` body
    - Include Bearer token in Authorization header
    - _Requirements: 3.2, 5.1_

  - [x] 5.3 Integrate ClubLogoUploader into PresMeet booking page
    - Add `ClubLogoUploader` component next to the "Presidents' Meeting Booking" heading
    - Pass `clubId` from authenticated user's Member record
    - Pass `isAdmin` based on user's role
    - _Requirements: 1.1_

- [x] 6. Frontend: Tests
  - [x] 6.1 Write Jest tests for ClubLogoUploader component
    - Test renders placeholder when no logo exists
    - Test renders image with correct src when logo exists
    - Test click triggers file input
    - Test file > 5MB shows error toast
    - Test successful upload updates image src
    - Test error response shows toast and reverts image
    - Test loading indicator visible during upload
    - _Requirements: 1.1, 1.2, 2.1, 2.3, 2.4, 2.5, 7.1, 7.2, 7.3_

- [x] 7. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python 3.11 with Pillow; frontend uses React 18 + TypeScript + Chakra UI
- The handler follows the project's one-function-per-endpoint convention with shared auth layer

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    {
      "id": 2,
      "tasks": [
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "3.6",
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "5.2"
      ]
    },
    { "id": 3, "tasks": ["5.1"] },
    { "id": 4, "tasks": ["5.3", "6.1"] }
  ]
}
```
