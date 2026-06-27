# Implementation Plan: i18n Error Messages

## Overview

Migrate all hardcoded Dutch error/validation strings across the frontend to `react-i18next` `t()` calls with interpolation, and connect the frontend to the backend's existing `error_key`-based localized error system. Uses a shared Validation_Helper utility, domain-owned validation keys, and the `common` namespace exclusively for cross-cutting concerns.

## Tasks

- [x] 1. Create Validation_Helper utility and locale infrastructure
  - [x] 1.1 Create `src/utils/validationMessages.ts` with `getValidationMessage` function
    - Export `ValidationRuleType` type and `ValidationParams` interface
    - Implement `getValidationMessage(t, ruleType, params?)` with `defaultValue` fallback for all 11 rule types
    - No hardcoded namespace — the caller's `t` determines resolution
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 11.1_

  - [x] 1.2 Write property tests for Validation_Helper (fast-check)
    - **Property 1: getValidationMessage always returns a non-empty string**
    - **Validates: Requirements 1.2, 11.1**
    - Test file: `frontend/src/__tests__/i18n/validationMessages.property.test.ts`
    - Use `fc.constantFrom(...)` for ruleType, arbitrary params
    - Mock `t` functions that return values AND that return undefined (simulating missing keys)

  - [x] 1.3 Write property test for namespace delegation
    - **Property 2: Namespace delegation — t function determines output**
    - **Validates: Requirements 1.8**
    - Two distinct mock `t` functions returning different strings must produce different results

- [x] 2. Add validation keys to domain namespace locale files
  - [x] 2.1 Add `validation` section to `products` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - Keys: required, email, min_length, max_length, min, max, pattern, invalid_number, invalid_option
    - Dutch translations must match current hardcoded messages
    - All keys use `{{variable}}` interpolation syntax where applicable
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.1, 10.6_

  - [x] 2.2 Add `validation` section to `members` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - Same key structure as products namespace
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.1, 10.6_

  - [x] 2.3 Add `validation` section to `eventBooking` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - Same key structure, plus any booking-specific keys
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.1, 10.6_

  - [x] 2.4 Add `validation` section to `webshop` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - Same key structure as products namespace
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.1, 10.6_

  - [x] 2.5 Add `validation` section to `events` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - Include poster-specific keys: `poster_invalid_type`, `poster_file_too_large`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 9.1, 9.2, 10.1, 10.6_

- [x] 3. Add common namespace extensions
  - [x] 3.1 Add `errors.*`, `notifications.*`, and `api_errors.*` sections to `common` namespace (all 8 languages, both `src/locales/` and `public/locales/`)
    - `errors`: network, unauthorized, forbidden, not_found, server_error, maintenance, timeout, unknown
    - `notifications`: action_success, action_error (with `{{action}}` interpolation)
    - `api_errors`: all 15 backend error keys (authorization_required, forbidden, not_found, validation_error, internal_error, member_not_found, member_already_exists, invalid_input, payment_failed, order_not_found, product_not_found, cart_empty, insufficient_stock, email_already_exists, invalid_membership)
    - Common namespace SHALL NOT contain any `validation.*` keys
    - _Requirements: 2.5, 2.6, 2.7, 6a.4, 10.4, 10.5_

- [x] 4. Checkpoint - Verify locale infrastructure
  - Ensure all tests pass, ask the user if questions arise.
  - Verify locale files are valid JSON in both `src/locales/` and `public/locales/`

- [x] 5. Migrate fieldRenderers.ts validateRule
  - [x] 5.1 Update `src/utils/fieldRenderers.ts` `validateRule` to accept optional `t` parameter
    - Import and call `getValidationMessage` when `t` is provided
    - Preserve fallback to Dutch strings when `t` is not passed (backward compat)
    - If `rule.message` is present and contains `:` (namespace prefix), call `t(rule.message)`
    - If `rule.message` is present without prefix, return it as literal string
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 11.2, 11.3_

  - [x] 5.2 Write property test for validateRule delegation
    - **Property 3: validateRule delegates to Validation_Helper when t is provided**
    - **Validates: Requirements 3.1**
    - For any rule type + failing value + t function, output matches `getValidationMessage`

  - [x] 5.3 Write property test for rule.message override
    - **Property 4: rule.message override takes priority**
    - **Validates: Requirements 3.3, 3.4**
    - rule.message without `:` → returned literally; with `:` → passed through `t()`

- [x] 6. Migrate Yup schemas in components
  - [x] 6.1 Migrate `MembershipFormModal.tsx` Yup schema to use Validation_Helper
    - Use `useTranslation('members')` and pass `t` to `getValidationMessage`
    - Replace hardcoded Dutch `.required()`, `.email()`, `.min()`, `.max()` messages
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Migrate `PaymentRecordForm.tsx` Yup schema to use Validation_Helper
    - Use `useTranslation('webshop')` for the `t` function
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.3 Migrate `ProductCard.tsx` Yup schema to use Validation_Helper
    - Use `useTranslation('products')` for the `t` function
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.4 Migrate `MemberApplicationForm.tsx` and `NewMemberApplicationForm.tsx` Yup schemas
    - Use `useTranslation('members')` for the `t` function
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.5 Migrate `MemberEditView.tsx` Yup schema to use Validation_Helper
    - Use `useTranslation('members')` for the `t` function
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 7. Migrate BookingWizard and ItemFieldsForm manual validation
  - [x] 7.1 Migrate `BookingWizard.tsx` `validateFormForSubmit()` to use i18n
    - Use `useTranslation('eventBooking')` and call `t('validation.required', { field })` instead of hardcoded strings
    - _Requirements: 5.1, 5.3_

  - [x] 7.2 Migrate `ItemFieldsForm.tsx` `validateSingleField()` to use Validation_Helper
    - Use `useTranslation('eventBooking')` and call `getValidationMessage(t, ruleType, params)`
    - _Requirements: 5.2, 5.4_

- [ ] 8. Migrate errorHandler.ts
  - [x] 8.1 Refactor `src/utils/errorHandler.ts` to use i18n
    - Replace `ERROR_MESSAGES` object with `getErrorMessages(t)` function using `common` namespace
    - Add `useTranslation('common')` inside `useErrorHandler` hook
    - Implement `getApiErrorMessage(t, errorKey)` for `api_errors.*` lookup
    - Use `t('notifications.action_error', { action })` and `t('notifications.action_success', { action })` for toast titles
    - Extend `ApiError` interface with `errorKey?: string`
    - Update `parseApiError` to extract `error_key` from response body
    - Implement priority chain: backend `error` field > `message` field > `error_key` lookup > status mapping
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6a.1, 6a.2, 6a.3, 6a.5_

  - [x] 8.2 Write unit tests for errorHandler priority chain
    - Test: response with specific `error` field displays it directly
    - Test: response with `message` but no `error` uses `message`
    - Test: response with `error_key` looks up `t('api_errors.{error_key}')`
    - Test: response with only status code falls back to `errors.*` mapping
    - Test: `handleSuccess` uses `t('notifications.action_success', { action })`
    - Test: `handleError` uses `t('notifications.action_error', { action })`
    - **Property 7: Error message priority — specific error preferred over generic message**
    - **Validates: Requirements 6a.2, 6a.3, 6a.5**
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6a.1, 6a.2, 6a.3, 6a.5_

- [x] 9. Checkpoint - Verify core migration
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` to verify type safety

- [x] 10. Migrate toast messages in admin components
  - [x] 10.1 Migrate `VariantSubTable.tsx` and `BulkVariantCreator.tsx` toasts
    - Use `useTranslation('products')` with keys under `products:toast.*`
    - Add `toast.*` keys to products namespace locale files (all 8 languages, both src/ and public/)
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 10.2 Migrate `AddStockForm.tsx` toasts and validation messages
    - Use `useTranslation('products')` with validation and toast keys
    - _Requirements: 7.1, 7.3_

  - [x] 10.3 Migrate `OrderDetailDrawer.tsx` status update toasts
    - Use `useTranslation('webshop')` with keys under `webshop:toast.*`
    - Add `toast.*` keys to webshop namespace locale files (all 8 languages, both src/ and public/)
    - _Requirements: 7.1, 7.4_

  - [x] 10.4 Migrate `PaymentRecordForm.tsx` success/error toasts
    - Use `useTranslation('webshop')` with keys under `webshop:toast.*`
    - _Requirements: 7.1, 7.6_

- [x] 11. Migrate member module validation
  - [x] 11.1 Migrate `GroupModal.tsx` and `UserModal.tsx` validation toasts
    - Use `useTranslation('members')` with `members:validation.*` keys
    - _Requirements: 8.1, 8.2_

  - [x] 11.2 Migrate `CsvUpload.tsx` file type error toast
    - Use `useTranslation('members')` with `members:errors.invalid_file_type` key
    - Add `errors.invalid_file_type` to members namespace (all 8 languages, both src/ and public/)
    - _Requirements: 8.3_

  - [x] 11.3 Migrate `OrderItemFieldsEditor.tsx` validation errors
    - Use `useTranslation('webshop')` with Validation_Helper for required/unique messages
    - _Requirements: 8.4_

- [x] 12. Migrate event module validation
  - [x] 12.1 Migrate `eventPosterUpload.ts` validation errors to return translation keys
    - Return `events:validation.poster_invalid_type` and `events:validation.poster_file_too_large` with interpolation
    - _Requirements: 9.1, 9.2_

- [ ] 13. Backend handler error_key adoption
  - [x] 13.1 Add `error_key` + `locale` to `submit_order` handler error responses
    - Use `resolve_request_locale(event)` from `shared.i18n.locale_resolver`
    - Include `error_key='validation_error'` for 400 errors, preserve existing `error` field
    - _Requirements: 12.1, 12.3, 12.4, 12.5_

  - [x] 13.2 Add `error_key` + `locale` to `update_order_items` handler error responses
    - Same pattern as submit_order
    - _Requirements: 12.1, 12.3, 12.4, 12.5_

  - [x] 13.3 Add `error_key` + `locale` to `update_product` handler error responses
    - Same pattern, include `forbidden` error_key for permission errors
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 13.4 Add `error_key` + `locale` to `update_event` handler error responses
    - Same pattern as update_product
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 13.5 Add `error_key` + `locale` to `update_payment` handler error responses
    - Same pattern as update_product
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 14. Checkpoint - Verify backend handlers
  - Ensure all tests pass, ask the user if questions arise.
  - Run `pytest tests/unit/test_submit_order.py tests/unit/test_update_product.py` to verify error_key adoption

- [x] 15. Property tests for locale file structure
  - [x] 15.1 Write property test for translation completeness across namespaces and locales
    - **Property 5: Translation completeness across all domain namespaces and locales**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    - Iterate all 5 domains × 8 locales, verify `validation` section with all required keys
    - Verify interpolation placeholders (`{{variable}}`) are present in keys that need them

  - [x] 15.2 Write property test for backend error_key coverage in common namespace
    - **Property 6: Backend error_key coverage in frontend common namespace**
    - **Validates: Requirements 6a.1, 6a.4**
    - All 15 error keys from backend must have matching `api_errors.*` entries in all 8 locales

  - [x] 15.3 Write property test for locale file synchronization
    - **Property 8: Locale file synchronization between src/ and public/**
    - **Validates: Requirements 10.6**
    - For every namespace file in `src/locales/{lang}/{ns}.json`, verify identical file at `public/locales/{lang}/{ns}.json`

- [x] 16. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` for type safety verification
  - Run ESLint on all modified files

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Always update BOTH `src/locales/` and `public/locales/` when adding translation keys (Requirement 10.6)
- Use `npx react-scripts test --watchAll=false --testPathPattern=...` for running specific tests
- Use `mcp_git_git_commit` for all commits (never shell git commit)
- Backend tests: `pytest tests/unit/test_<handler>.py` for specific handlers

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "2.2", "2.3", "2.4", "2.5", "3.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "5.1"] },
    {
      "id": 2,
      "tasks": ["5.2", "5.3", "6.1", "6.2", "6.3", "6.4", "6.5", "7.1", "7.2"]
    },
    {
      "id": 3,
      "tasks": [
        "8.1",
        "10.1",
        "10.2",
        "10.3",
        "10.4",
        "11.1",
        "11.2",
        "11.3",
        "12.1"
      ]
    },
    { "id": 4, "tasks": ["8.2", "13.1", "13.2", "13.3", "13.4", "13.5"] },
    { "id": 5, "tasks": ["15.1", "15.2", "15.3"] }
  ]
}
```
