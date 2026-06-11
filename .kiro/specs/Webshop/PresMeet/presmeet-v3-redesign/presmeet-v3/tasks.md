# Implementation Plan: PresMeet v3 Immediate Fixes

## Overview

This plan implements 12 targeted fixes across the PresMeet booking system — PDF generation, booking overview enhancements, onboarding UX, cart builder extraction, validation, backend payment handler fix, admin contrast fixes, product modal fixes, and Cognito permission assignment. Frontend uses TypeScript/React/Chakra UI with Jest + fast-check for testing. Backend uses Python with pytest + hypothesis.

## Tasks

- [x] 1. Create PDF Generator utility and cart builder extraction
  - [x] 1.1 Create `pdfGenerator.ts` utility with `preparePdfData`, `generateBookingPdf`, and `buildPdfFilename` functions
    - Create file `frontend/src/modules/presmeet/utils/pdfGenerator.ts`
    - Implement `PdfBookingData`, `PdfLineItem`, `PdfGroupData` interfaces
    - Implement `preparePdfData` that groups cart items by product type, computes line totals (persons × unit_price for transfers, 1 × unit_price for others), and returns `PdfGroupData[]`
    - Implement `generateBookingPdf` using jsPDF + jspdf-autotable to render grouped items, club name header, grand total, and conditional payment instructions (when payment_status is "unpaid" or "partial")
    - Implement `buildPdfFilename(clubId)` returning `presmeet-booking-{clubId}.pdf`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 Extract cart builder utility into `cartBuilder.ts`
    - Create file `frontend/src/modules/presmeet/utils/cartBuilder.ts`
    - Define `CartBuildResult` interface with `items`, `totalAmount`, `itemCount`
    - Implement `buildCartItems(formData, config)` that generates cart items from form data
    - Ensure `party_ticket` items are generated for delegates with `attend_party: true` (with delegate name in attributes, person_type "delegate")
    - Ensure `airport_transfer` items carry `persons` attribute from form data
    - Ensure total calculation multiplies transfer unit_price × persons
    - _Requirements: 7.1, 7.2, 7.3, 8.1, 8.2_

  - [x] 1.3 Write property tests for PDF generator (Properties 1, 2, 3)
    - Create file `frontend/src/modules/presmeet/__tests__/pdfGenerator.property.test.ts`
    - **Property 1: PDF data preparation produces correct grouped output** — for any valid cart items, `preparePdfData` groups items by product_type, each group's items sum to group total, all group totals sum to grand total
    - **Property 2: PDF includes payment instructions conditionally** — for payment_status "unpaid"/"partial" output includes payment instructions; for "paid" it does not
    - **Property 3: PDF filename matches expected pattern** — for any club_id, `buildPdfFilename` returns `presmeet-booking-{clubId}.pdf`
    - Use fast-check with minimum 100 iterations
    - **Validates: Requirements 1.1, 1.2, 1.4, 1.5**

  - [x] 1.4 Write property tests for cart builder (Properties 8, 9)
    - Create file `frontend/src/modules/presmeet/__tests__/cartBuilder.property.test.ts`
    - **Property 8: Delegate party ticket cart item generation** — for any delegate with attend_party true, buildCartItems produces a party_ticket item with that delegate's name and person_type "delegate"
    - **Property 9: Order total includes delegate party tickets** — for N delegates with attend_party true, total includes N × party_ticket_unit_price
    - Use fast-check with minimum 100 iterations
    - **Validates: Requirements 7.1, 7.2, 7.3, 2.1**

- [x] 2. Enhance BookingOverview component
  - [x] 2.1 Add delegate party ticket line items and transfer persons display to BookingOverview
    - Modify `frontend/src/modules/presmeet/components/BookingOverview.tsx`
    - Update props interface to include `clubName`, `clubId`, `paymentStatus`, `totalPaid`, `submittedAt`
    - Display delegate party tickets as line items in the party_ticket product group (with delegate name)
    - Display persons count and computed line total (persons × unit_price) for airport transfers with persons > 1
    - Display submission date when order status is "submitted" or "locked"
    - Display summary section with grand total, total paid, and remaining balance
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 8.3_

  - [x] 2.2 Add PDF download button to BookingOverview
    - Add a download button that calls `generateBookingPdf` with the current booking data
    - Wire `clubName`, `items`, `status`, `paymentStatus`, `totalPaid`, `submittedAt` into the PDF generator
    - Handle PDF generation errors with a toast notification
    - _Requirements: 1.1, 1.5_

  - [x] 2.3 Write property tests for booking calculations (Properties 4, 5, 10)
    - Create file `frontend/src/modules/presmeet/__tests__/bookingCalculations.property.test.ts`
    - **Property 4: Booking overview totals include all items correctly** — grand total equals sum of all group line totals, accounting for delegate party tickets and persons × unit_price for transfers
    - **Property 5: Remaining balance calculation** — for any grandTotal and totalPaid ≥ 0, remaining = max(0, grandTotal - totalPaid)
    - **Property 10: Transfer quantity multiplication** — for any transfer item with persons P ≥ 1, line total = P × unit_price
    - Use fast-check with minimum 100 iterations
    - **Validates: Requirements 2.2, 2.3, 3.2, 8.1, 8.2, 8.3**

- [x] 3. Checkpoint - Ensure PDF and booking overview tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance OnboardingFlow and validation
  - [x] 4.1 Add club search functionality to OnboardingFlow
    - Modify `frontend/src/modules/presmeet/components/OnboardingFlow.tsx`
    - Add search input field (`<Input>`) above the club grid
    - Implement `filterClubs(clubs, searchText)` with case-insensitive name matching
    - Display "no results" message when filter yields empty list
    - Add `searchText` state and wire to the filter
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.2 Add logo animation to OnboardingFlow
    - Add `logosSmall` state, initially false
    - Display Presmeet logo and FH-DCE logo centered at large size (minimum 120px height) on initial load
    - Transition logos to small versions (max 40px height) at top of page after scroll or animation timer
    - Use CSS transition with minimum 300ms duration for smooth size change
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 4.3 Add party ticket name validation
    - Create or modify `frontend/src/modules/presmeet/utils/validation.ts`
    - Implement `validatePartyTicketName(item)` — returns error if name is empty, whitespace-only, or missing
    - Implement `validateBookingSubmission(items)` — validates all party_ticket items have names
    - Block submission with inline error message when validation fails
    - _Requirements: 9.1, 9.2_

  - [x] 4.4 Write property tests for club search (Property 6)
    - Create file `frontend/src/modules/presmeet/__tests__/clubSearch.property.test.ts`
    - **Property 6: Club search filter returns correct results** — for any club list and search string, filter returns exactly clubs whose name contains search text (case-insensitive); empty search returns all
    - Use fast-check with minimum 100 iterations
    - **Validates: Requirements 4.1, 4.2**

  - [x] 4.5 Write property tests for party ticket name validation (Property 11)
    - Create file `frontend/src/modules/presmeet/__tests__/validation.property.test.ts`
    - **Property 11: Party ticket name validation** — for any party_ticket item with empty, whitespace-only, or missing name, validation produces an error
    - Use fast-check with minimum 100 iterations
    - **Validates: Requirements 9.1, 9.2**

- [x] 5. Checkpoint - Ensure onboarding and validation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Fix admin payment handler (backend)
  - [x] 6.1 Fix error handling in `admin_record_payment` handler
    - Modify `backend/handler/admin_record_payment/app.py`
    - Add input validation for `order_id`, `amount` (numeric, range 0.01–999999.99), `date` (valid format), `description`
    - Return 400 with descriptive field-specific error messages for invalid input
    - Catch `botocore.exceptions.ClientError` for DynamoDB errors, return 500 with structured `{ "error": "Internal server error", "error_code": "DYNAMO_ERROR" }`, log full exception
    - Ensure generic `except Exception` returns structured JSON error (not plain string)
    - Add JSON decode error handling returning 400
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 6.2 Write property tests for payment handler validation (Property 7)
    - Create file `backend/tests/unit/test_admin_record_payment_properties.py`
    - **Property 7: Payment handler input validation** — for any payload missing order_id, non-numeric amount, amount outside [0.01, 999999.99], missing date, or invalid date format, handler returns 400 and does NOT modify database
    - Use hypothesis with minimum 100 iterations
    - **Validates: Requirements 6.1**

- [x] 7. Fix admin dashboard and product modal contrast
  - [x] 7.1 Fix admin dashboard text contrast
    - Modify `frontend/src/modules/presmeet/components/AdminDashboard.tsx`
    - Replace low-contrast color values (e.g. `color="gray.400"`) with WCAG AA compliant values (`color="gray.700"` or darker on white backgrounds)
    - Ensure all data cells use sufficient contrast (minimum 4.5:1 ratio)
    - _Requirements: 10.1, 10.2_

  - [x] 7.2 Fix product modal text contrast and purchase rules dropdown
    - Modify product modal component in `frontend/src/modules/products/`
    - Fix variant schema text contrast to meet WCAG AA (4.5:1)
    - Fix purchase rules (aankoopregels) text contrast to meet WCAG AA (4.5:1)
    - Populate purchase rules dropdown from product configuration data instead of hardcoded empty content
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 8. Cognito webmaster permissions
  - [x] 8.1 Add event administration permissions to webmaster role
    - Create or update script (using `fix_webmaster_roles.py` pattern) to add `Events_Read`, `Events_Export`, `Events_CRUD` permissions to the webmaster Cognito user pool group
    - Ensure the webmaster user (webmaster@h-dcn.nl) gets access to the event administration module
    - _Requirements: 12.1, 12.2_   (Was already implemented)

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–11)
- Frontend tests use Jest + fast-check; backend tests use pytest + hypothesis
- All property tests configured for minimum 100 iterations
- The cart builder extraction (1.2) enables testable isolation of booking calculation logic
- PDF generation is client-side only (jsPDF + jspdf-autotable), no backend PDF service needed
- Cognito permission changes (task 8.1) use the existing `fix_webmaster_roles.py` script pattern with `--profile nonprofit-deploy`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "4.3", "6.1", "7.1", "7.2", "8.1"] },
    { "id": 1, "tasks": ["1.3", "1.4", "2.1", "4.1", "4.2", "4.5", "6.2"] },
    { "id": 2, "tasks": ["2.2", "2.3", "4.4"] }
  ]
}
```
