# Implementation Plan: Multi-Language Support

## Overview

Implement internationalization (i18n) for the H-DCN member portal and webshop, supporting 8 European languages (nl, en, fr, de, sv, da, it, es) across the React frontend, Python Lambda backend, email templates, and PDF generation, while keeping the admin panel Dutch-only. The implementation uses react-i18next on the frontend, a shared i18n module in the Lambda layer for the backend, and the browser Intl API for locale-aware formatting.

## Tasks

- [x] 1. Set up frontend i18n infrastructure
  - [x] 1.1 Install and configure react-i18next with lazy-loading
    - Install `react-i18next`, `i18next`, `i18next-http-backend` packages
    - Create `frontend/src/i18n/constants.ts` with `SUPPORTED_LOCALES` array and namespace definitions
    - Create `frontend/src/i18n/index.ts` initializing i18next with HttpBackend, fallback `nl`, load path `/locales/{{lng}}/{{ns}}.json`, namespaces (common, dashboard, webshop, members, events, products, auth), React Suspense integration, and `parseMissingKeyHandler` returning key as visible text
    - Create `frontend/src/i18n/localeResolver.ts` with `resolveLocale`, `parseBrowserLocale`, and `isValidLocale` functions
    - Wrap the App component with `I18nextProvider` and Suspense boundary
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 1.2 Write property tests for locale resolution (frontend)
    - **Property 1: Locale resolution priority**
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.5**
    - Use fast-check to generate combinations of stored preference (valid/invalid/null) and browser locale (supported/unsupported/malformed)
    - Verify priority: stored preference → browser language → Dutch default

  - [x] 1.3 Write property tests for translation fallback chain (frontend)
    - **Property 2: Translation fallback chain**
    - **Validates: Requirements 1.5, 1.6**
    - Use fast-check to verify missing/empty keys fall back to Dutch, then to key string itself

  - [x] 1.4 Create Dutch reference translation files for all namespaces
    - Create `frontend/src/locales/nl/common.json` with shared UI strings (nav, footer, buttons, generic labels)
    - Create `frontend/src/locales/nl/dashboard.json`, `webshop.json`, `members.json`, `events.json`, `products.json`, `auth.json`
    - Ensure key naming follows pattern `^[a-z][a-z0-9_.]*[a-z0-9]$` with max 2 levels nesting
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 1.5 Write property tests for translation file conventions (frontend)
    - **Property 11: Translation file key naming convention**
    - **Property 12: Translation file maximum nesting depth**
    - **Validates: Requirements 10.2, 10.3**
    - Use fast-check to validate key patterns and nesting depth constraints

- [x] 2. Implement locale formatting utilities and Language Selector
  - [x] 2.1 Create format utilities module
    - Create `frontend/src/utils/formatLocale.ts` with `formatDate(date, style, locale)`, `formatCurrency(amount, locale)`, `formatNumber(value, locale)` using Intl APIs
    - Return empty string for null/undefined/NaN/unparseable values
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 2.2 Write property tests for format utilities
    - **Property 5: Locale-aware formatting produces valid output**
    - **Property 6: Invalid format input returns empty string**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**
    - Use fast-check to test formatting with arbitrary valid dates/numbers/locales and invalid inputs

  - [x] 2.3 Implement LanguageSelector component
    - Create `frontend/src/components/common/LanguageSelector.tsx` as a Chakra UI Menu
    - Display all 8 locales with flag icons and native language names
    - Highlight active locale (bold + checkmark in expanded state)
    - On selection: call `i18n.changeLanguage(locale)` and persist via `PUT /members/{id}` with `{ preferred_language: locale }`
    - On persist failure: show non-blocking toast, keep local locale active
    - Ensure WCAG 2.1 AA accessibility (keyboard navigation, contrast)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 2.6, 2.7, 2.8_

  - [x] 2.4 Write unit tests for LanguageSelector
    - Test rendering of all 8 locales with flags and native names
    - Test active locale highlighting
    - Test keyboard navigation accessibility
    - Test language switch triggers `i18n.changeLanguage`
    - Test error toast on persist failure
    - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 2.5 Write property tests for interpolation
    - **Property 3: Interpolation preserves dynamic values**
    - **Validates: Requirements 4.3**
    - Use fast-check to verify that all interpolation values appear in rendered output

  - [x] 2.6 Write property tests for plural form selection
    - **Property 4: Plural form selection follows CLDR rules**
    - **Validates: Requirements 4.4**
    - Use fast-check to test plural form suffix selection for various locales and count values

- [x] 3. Implement admin locale override and Accept-Language header
  - [x] 3.1 Create admin locale override hook
    - Create `frontend/src/hooks/useAdminLocale.ts` with `useIsAdminRoute()` and `useAdminLocaleOverride()` functions
    - Admin routes: `/members`, `/products`, `/events`, `/memberships`, `/advanced-exports`
    - Switch locale to `nl` on admin routes, restore user preference on member-facing routes
    - Hide LanguageSelector on admin routes
    - _Requirements: 9.1, 9.3, 9.4, 9.5, 9.6_

  - [x] 3.2 Write property test for admin locale override round-trip
    - **Property 10: Admin locale override round-trip**
    - **Validates: Requirements 9.1, 9.3, 9.4, 9.5, 9.6, 3.1**
    - Use fast-check to verify locale switches to nl on admin routes and restores on member routes

  - [x] 3.3 Add Accept-Language header to API requests
    - Extend `frontend/src/utils/authHeaders.ts` `getAuthHeaders()` to include `Accept-Language: {i18n.language}`
    - _Requirements: 6.1_

  - [x] 3.4 Write unit tests for admin route detection and Accept-Language header
    - Test `useIsAdminRoute` correctly identifies admin vs member routes
    - Test `getAuthHeaders` includes Accept-Language header with active locale
    - _Requirements: 9.1, 6.1_

- [x] 4. Checkpoint - Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement backend i18n shared module
  - [x] 5.1 Create locale resolver module
    - Create `backend/layers/auth-layer/python/shared/i18n/__init__.py` with module exports
    - Create `backend/layers/auth-layer/python/shared/i18n/locale_resolver.py` with `SUPPORTED_LOCALES`, `DEFAULT_LOCALE`, `resolve_request_locale(event)`, `resolve_member_locale(preferred_language)`, `is_valid_locale(locale)`
    - Parse Accept-Language header, validate against supported locales, fallback to nl
    - _Requirements: 6.3, 6.4, 6.5_

  - [x] 5.2 Write property test for backend locale resolution
    - **Property 1: Locale resolution priority (backend)**
    - **Validates: Requirements 6.3, 6.4**
    - Use Hypothesis to test `resolve_request_locale` and `resolve_member_locale` with valid/invalid/missing locales

  - [x] 5.3 Create error messages module
    - Create `backend/layers/auth-layer/python/shared/i18n/error_messages.py` with `ERROR_MESSAGES` dict and `get_error_message(error_key, locale)` function
    - Include translations for all common API errors across 8 locales
    - Fallback to Dutch for unknown locales or missing keys
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 5.4 Write property test for error message localization
    - **Property 7: Backend error message localization with fallback**
    - **Validates: Requirements 6.2, 6.3, 6.4**
    - Use Hypothesis to test `get_error_message` returns non-empty messages for valid locales and Dutch fallback for invalid ones

  - [x] 5.5 Create PDF translations module
    - Create `backend/layers/auth-layer/python/shared/i18n/pdf_translations.py` with `PDF_TRANSLATIONS` dict, `get_pdf_text(key, locale)`, `format_date_for_locale(date, locale)`, `format_currency_for_locale(amount, locale)`
    - Include translations for document title, section headings, table headers, field labels, totals, status values for all 8 locales
    - _Requirements: 8.2, 8.3, 8.5_

  - [x] 5.6 Write property tests for PDF translations
    - **Property 8: PDF translation completeness**
    - **Property 9: Backend locale-aware date and currency formatting**
    - **Validates: Requirements 8.2, 8.3, 8.5, 7.6**
    - Use Hypothesis to verify all PDF keys return non-empty strings for all locales, and formatting produces valid output

  - [x] 5.7 Update CORS headers to allow Accept-Language
    - Update `cors_headers()` in `backend/layers/auth-layer/python/shared/auth_utils.py` to include `Accept-Language` in `Access-Control-Allow-Headers`
    - _Requirements: 6.1_

- [x] 6. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Integrate backend i18n into API handlers and PDF generator
  - [x] 7.1 Integrate localized error responses into existing handlers
    - Update `create_error_response()` in `auth_utils.py` to accept locale parameter and include both `error_key` and localized `message` in error responses
    - Update key handlers (create_order, create_payment, create_member, update_member) to resolve locale from Accept-Language header and pass to error responses
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 7.2 Integrate PDF translations into order confirmation generator
    - Update the order confirmation PDF handler to read member's `preferred_language` from Members table
    - Replace hardcoded Dutch text with `get_pdf_text()` calls using resolved locale
    - Use `format_date_for_locale()` and `format_currency_for_locale()` for date/currency values in PDF
    - Fallback to nl for invalid/missing preferred_language
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.3 Write unit tests for localized error responses and PDF integration
    - Test error response contains both `error_key` and localized `message`
    - Test PDF generates with correct locale translations
    - Test fallback to Dutch for missing/invalid locale
    - _Requirements: 6.2, 8.1, 8.4_

- [x] 8. Implement email template localization
  - [x] 8.1 Restructure email templates into locale directories
    - Move existing templates from `backend/email-templates/templates/` to `backend/email-templates/templates/nl/`
    - Create locale subdirectories for en, fr, de, sv, da, it, es
    - Create translated versions of: membership-application-confirmation.html, welcome-user.html, passwordless-recovery.html, resend-code.html for all locales
    - _Requirements: 7.3, 7.5_

  - [x] 8.2 Create email locale resolution utility
    - Create `backend/layers/auth-layer/python/shared/i18n/email_utils.py` with helper to resolve email locale from member's preferred_language
    - Template loading: resolve from `templates/{locale}/` with fallback to `templates/nl/`
    - Format dates and currency in emails using locale conventions
    - _Requirements: 7.1, 7.2, 7.4, 7.6_

  - [x] 8.3 Update Cognito custom message Lambda for locale support
    - Update `backend/handler/cognito_custom_message/app.py` to read `clientMetadata.locale` from event
    - Select email template based on resolved locale
    - Fallback to Dutch if locale is absent or invalid
    - _Requirements: 11.4, 11.5_

  - [x] 8.4 Write unit tests for email template selection and Cognito locale handling
    - Test template path resolution per locale
    - Test fallback to Dutch templates for missing locales
    - Test Cognito custom message reads clientMetadata.locale correctly
    - _Requirements: 7.1, 7.2, 7.4, 11.4, 11.5_

- [x] 9. Extract and translate frontend text
  - [x] 9.1 Extract hardcoded Dutch text from member-facing components
    - Replace hardcoded Dutch strings in member-facing React components with `t('namespace.key')` calls
    - Cover: page headings, button labels, form labels, placeholders, validation messages, status messages, navigation items, card descriptions, tooltips, modal titles, table headers, confirmation dialogs
    - Pass dynamic values as interpolation parameters
    - Add plural form suffixes (\_one/\_other) where count-dependent text exists
    - Do NOT translate admin panel pages, proper nouns, brand names, or user-generated content
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6_

  - [x] 9.2 Create translation files for all non-Dutch locales
    - Create `frontend/src/locales/{en,fr,de,sv,da,it,es}/` directories
    - Create translated JSON files for all 7 namespaces in each locale
    - Ensure all keys from Dutch reference files are present in every locale
    - _Requirements: 1.4, 10.1, 10.4_

  - [x] 9.3 Translate authentication flow UI strings
    - Ensure auth namespace covers login prompts, error messages, passkey instructions, email verification messages for all 8 locales
    - Pass browser locale as clientMetadata when calling Cognito signUp/signIn
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 9.4 Write unit tests for text extraction completeness
    - Verify no hardcoded Dutch strings remain in member-facing components
    - Verify all translation keys used in components exist in Dutch reference files
    - _Requirements: 4.1, 4.2_

- [x] 10. Add missing key development warnings and namespace lazy loading validation
  - [x] 10.1 Implement development-mode missing key warnings
    - Configure i18next `missingKeyHandler` to log warnings to browser console in development mode identifying locale, namespace, and missing key name
    - Treat empty string values as missing (fallback to Dutch)
    - Ensure namespace files lazy-load correctly per route and display Dutch fallback on load failure
    - _Requirements: 10.5, 10.6, 1.7, 4.5_

  - [x] 10.2 Write unit tests for missing key handler and namespace loading
    - Test console warning output format
    - Test empty string values trigger Dutch fallback
    - Test failed namespace load falls back to Dutch
    - _Requirements: 10.5, 10.6, 4.5_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Frontend uses TypeScript with react-i18next and fast-check for property tests
- Backend uses Python 3.11 with Hypothesis for property tests
- Admin panel remains Dutch-only — no translation work needed for admin pages
- Translation files use JSON format with max 2 levels nesting and lowercase key convention

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "5.2", "5.3", "5.5", "5.7"] },
    { "id": 2, "tasks": ["1.5", "2.1", "5.4", "5.6"] },
    {
      "id": 3,
      "tasks": ["2.2", "2.3", "2.5", "2.6", "3.3", "7.1", "7.2", "8.2"]
    },
    { "id": 4, "tasks": ["2.4", "3.1", "7.3", "8.1", "8.3"] },
    { "id": 5, "tasks": ["3.2", "3.4", "8.4", "9.1"] },
    { "id": 6, "tasks": ["9.2", "9.3"] },
    { "id": 7, "tasks": ["9.4", "10.1"] },
    { "id": 8, "tasks": ["10.2"] }
  ]
}
```
