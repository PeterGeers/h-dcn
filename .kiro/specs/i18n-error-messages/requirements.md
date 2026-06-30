# Requirements Document

## Introduction

Refactor all hardcoded error and validation messages across the frontend codebase to use react-i18next `t()` calls with interpolation. The application currently has 15+ files with hardcoded Dutch strings in Yup validation schemas, manual form validation, toast notifications, and the `errorHandler.ts` utility.

The backend already has a complete i18n error system (`shared.i18n.error_messages`) that sends `error_key` + locale-resolved `message` in API responses — but the frontend ignores this and displays its own hardcoded strings. This spec connects the two: the frontend will consume the backend's `error_key`-based localized messages for API errors, and use a generic validation helper with `t()` interpolation (e.g., `t('validation.required', { field })`) for client-side form validation. Each domain module owns its own validation and error translations in its namespace (e.g., `products:validation.required`, `eventBooking:validation.required`). Only truly cross-cutting concerns (network timeout, unauthorized, server error) live in the `common` namespace. The result is that error messages become more relevant (backend can include field-specific detail like "field X aspect Y") AND translated into all 8 languages.

## Glossary

- **Validation_Helper**: A shared utility function (`getValidationMessage`) that accepts a `t` function (already bound to the calling domain's namespace) and a validation rule type with optional parameters, returning a translated error string via `t()` using the domain's own `validation.*` keys
- **Domain_Namespace**: The i18n namespace specific to each module (e.g., `products`, `eventBooking`, `webshop`, `members`) that owns its own validation and error translation keys under `validation.*` and `errors.*` sections
- **Common_Namespace**: The `common` i18n namespace (`locales/{lang}/common.json`) reserved exclusively for truly cross-cutting concerns: network errors, auth failures, server errors, and maintenance messages — NOT validation messages
- **Field_Renderers**: The utility at `src/utils/fieldRenderers.ts` containing `validateRule()` with hardcoded Dutch validation messages
- **Error_Handler**: The utility at `src/utils/errorHandler.ts` providing `ERROR_MESSAGES` constants and the `useErrorHandler` hook with hardcoded Dutch strings
- **Toast_Message**: A Chakra UI `useToast()` notification displayed to the user for success, error, or warning feedback
- **Yup_Schema**: A Formik validation schema object built with the Yup library, containing validation rules and error messages
- **Interpolation**: react-i18next variable substitution in translation strings using `{{variable}}` syntax
- **Error_Key**: A stable string identifier (e.g., `validation_error`, `member_not_found`) sent by the backend in error responses, used to look up localized messages
- **Backend_i18n**: The existing `shared.i18n.error_messages` module that resolves `error_key` + `locale` to a translated error message (already supports all 8 locales)

## Requirements

### Requirement 1: Generic Validation Message Helper

**User Story:** As a developer, I want a shared validation message helper that returns translated error strings using the calling domain's namespace, so that all forms use consistent i18n-aware validation messages while each domain owns its own translations.

#### Acceptance Criteria

1. THE Validation_Helper SHALL export a function `getValidationMessage(t, ruleType, params?)` that returns a translated string for the given validation rule type, where `t` is the translation function from the calling domain's namespace
2. THE Validation_Helper SHALL support the following rule types: `required`, `email`, `phone`, `iban`, `min_length`, `max_length`, `min`, `max`, `pattern`, `invalid_number`, `invalid_option`
3. WHEN `ruleType` is `required`, THE Validation_Helper SHALL return `t('validation.required', { field: params.field })` using the field label as interpolation
4. WHEN `ruleType` is `min_length`, THE Validation_Helper SHALL return `t('validation.min_length', { count: params.count })` with the minimum character count
5. WHEN `ruleType` is `max_length`, THE Validation_Helper SHALL return `t('validation.max_length', { count: params.count })` with the maximum character count
6. WHEN `ruleType` is `min`, THE Validation_Helper SHALL return `t('validation.min', { value: params.value })` with the minimum numeric value
7. WHEN `ruleType` is `max`, THE Validation_Helper SHALL return `t('validation.max', { value: params.value })` with the maximum numeric value
8. THE Validation_Helper SHALL NOT hardcode a namespace — the `t` function passed by the caller determines which namespace the `validation.*` keys resolve from (e.g., `products:validation.required`, `eventBooking:validation.required`)
9. THE Validation_Helper SHALL be located at `src/utils/validationMessages.ts`

### Requirement 2: Domain Namespace Validation Keys

**User Story:** As a user, I want to see validation messages in my preferred language, so that form errors are understandable regardless of language setting.

#### Acceptance Criteria

1. EACH Domain_Namespace SHALL contain a `validation` section with keys for the rule types used in that domain (e.g., `products:validation.required`, `eventBooking:validation.required`, `webshop:validation.required`)
2. EACH Domain_Namespace SHALL provide Dutch (`nl`) translations that match the current hardcoded messages (e.g., `"{{field}} is verplicht"`)
3. EACH Domain_Namespace SHALL provide translations for all 8 languages: nl, en, de, fr, es, it, da, sv
4. WHEN a validation key uses interpolation, THE Domain_Namespace SHALL use react-i18next `{{variable}}` syntax
5. THE Common_Namespace SHALL contain ONLY cross-cutting error keys: `errors.network`, `errors.unauthorized`, `errors.forbidden`, `errors.not_found`, `errors.server_error`, `errors.maintenance`, `errors.timeout`, `errors.unknown`
6. THE Common_Namespace SHALL contain a `notifications` section with interpolated keys for success and error toast patterns: `action_success` (`{{action}} succesvol`), `action_error` (`Fout bij {{action}}`)
7. THE Common_Namespace SHALL NOT contain validation messages — those belong in each domain's namespace

### Requirement 3: Migrate Field_Renderers Validation

**User Story:** As a developer, I want the `fieldRenderers.ts` validateRule function to use the Validation_Helper, so that field registry validation produces translated messages.

#### Acceptance Criteria

1. WHEN the Field_Renderers `validateRule` function produces an error message, THE Field_Renderers SHALL call the Validation_Helper instead of returning hardcoded Dutch strings
2. THE Field_Renderers SHALL accept a `t` function parameter (from `useTranslation` with the calling module's namespace) to pass to the Validation_Helper
3. THE Field_Renderers SHALL preserve existing fallback behavior where `rule.message` overrides the generic message if provided in the field registry
4. IF a `rule.message` contains a translation key (prefixed with a namespace), THEN THE Field_Renderers SHALL call `t(rule.message)` instead of using it as a literal string

### Requirement 4: Migrate Yup Schema Validation Messages

**User Story:** As a developer, I want Yup validation schemas to use i18n messages from the domain namespace, so that Formik form errors display in the user's language.

#### Acceptance Criteria

1. WHEN a Yup schema uses `.required()` with a hardcoded string, THE Yup_Schema SHALL use a function that calls the Validation_Helper with the domain's `t` function: `.required(() => getValidationMessage(t, 'required', { field }))`
2. WHEN a Yup schema uses `.email()` with a hardcoded string, THE Yup_Schema SHALL use a function that calls the Validation_Helper for the `email` rule type
3. WHEN a Yup schema uses `.min()` or `.max()` with a hardcoded message, THE Yup_Schema SHALL use the Validation_Helper with appropriate parameters
4. THE Yup_Schema migrations SHALL apply to these files: `MembershipFormModal.tsx`, `PaymentRecordForm.tsx`, `ProductCard.tsx`, `MemberApplicationForm.tsx`, `MemberEditView.tsx`, `NewMemberApplicationForm.tsx`
5. EACH component SHALL use its own domain namespace for the `t` function (e.g., `useTranslation('members')` for member forms, `useTranslation('products')` for product forms, `useTranslation('webshop')` for payment forms)

### Requirement 5: Migrate Manual Validation in Booking Forms

**User Story:** As a user booking an event, I want to see validation errors in my language, so that I understand what fields need attention.

#### Acceptance Criteria

1. WHEN `BookingWizard.tsx` `validateFormForSubmit()` detects a missing required field, THE BookingWizard SHALL use `t('validation.required', { field })` from the `eventBooking` namespace instead of hardcoded English strings
2. WHEN `ItemFieldsForm.tsx` `validateSingleField()` detects a validation error, THE ItemFieldsForm SHALL use the Validation_Helper with the `eventBooking` namespace `t` function instead of hardcoded Dutch strings
3. THE BookingWizard SHALL use the `eventBooking` namespace for validation messages (validation keys live in `eventBooking:validation.*`)
4. THE ItemFieldsForm SHALL use the `eventBooking` namespace for validation messages (validation keys live in `eventBooking:validation.*`)

### Requirement 6: Migrate Error_Handler Utility

**User Story:** As a developer, I want the centralized error handler to produce translated messages from the `common` namespace (for cross-cutting errors only), so that API error toasts display in the user's language.

#### Acceptance Criteria

1. THE Error_Handler `ERROR_MESSAGES` object SHALL be replaced with a function `getErrorMessages(t)` that returns translated messages using `t('errors.{type}')` from the `common` namespace (only for cross-cutting errors like network, auth, server)
2. THE Error_Handler `useErrorHandler` hook SHALL use `useTranslation('common')` internally and pass `t` to the message resolver
3. WHEN `useErrorHandler.handleError` is called, THE Error_Handler SHALL use `t('notifications.action_error', { action: context })` for the toast title
4. WHEN `useErrorHandler.handleSuccess` is called, THE Error_Handler SHALL use `t('notifications.action_success', { action: context })` for the toast title
5. THE Error_Handler SHALL export a `getApiErrorMessage(t, status)` function for mapping HTTP status codes to translated messages from the `common` namespace

### Requirement 6a: Consume Backend Error_Key in API Responses

**User Story:** As a user, I want to see the specific error message the backend provides (e.g., "Member not found", "Insufficient stock") in my language, so that I understand exactly what went wrong.

#### Acceptance Criteria

1. WHEN an API response contains an `error_key` field, THE Error_Handler SHALL use it to look up a frontend translation key: `t('api_errors.{error_key}')` from the `common` namespace (these are cross-cutting API errors, not validation messages)
2. WHEN an API response contains both `error_key` and `message`, THE Error_Handler SHALL prefer the `message` field (already localized by the backend) and use `error_key` only as fallback lookup
3. WHEN an API response contains a `message` field (from backend i18n), THE Error_Handler SHALL display it directly instead of mapping from HTTP status code
4. THE Common_Namespace SHALL contain an `api_errors` section with keys matching the backend `ERROR_MESSAGES` keys: `authorization_required`, `forbidden`, `not_found`, `validation_error`, `internal_error`, `member_not_found`, `member_already_exists`, `invalid_input`, `payment_failed`, `order_not_found`, `product_not_found`, `cart_empty`, `insufficient_stock`, `email_already_exists`, `invalid_membership`
5. WHEN the backend sends a detailed error message (e.g., `"Missing required parameter: regio"`) without an error_key, THE Error_Handler SHALL display the backend message directly (more specific than any generic mapping)

### Requirement 7: Migrate Toast Messages in Admin Components

**User Story:** As an admin, I want toast notifications in my language, so that success and error feedback is understandable.

#### Acceptance Criteria

1. WHEN admin components in `modules/webshop-management/` display toast messages, THE components SHALL use `t()` calls with their domain namespace keys instead of hardcoded Dutch strings
2. WHEN `VariantSubTable.tsx` shows success/error toasts, THE component SHALL use `useTranslation('products')` with keys under `products:toast.*`
3. WHEN `AddStockForm.tsx` shows validation or success toasts, THE component SHALL use `useTranslation('products')` with validation keys under `products:validation.*`
4. WHEN `OrderDetailDrawer.tsx` shows status update toasts, THE component SHALL use `useTranslation('webshop')` with keys under `webshop:toast.*`
5. WHEN `BulkVariantCreator.tsx` shows creation results, THE component SHALL use `useTranslation('products')` with keys under `products:toast.*`
6. WHEN `PaymentRecordForm.tsx` shows success/error toasts, THE component SHALL use `useTranslation('webshop')` with keys under `webshop:toast.*`

### Requirement 8: Migrate Member Module Validation

**User Story:** As an admin managing members, I want validation and feedback messages in my language, so that the admin interface is consistent with the rest of the portal.

#### Acceptance Criteria

1. WHEN `GroupModal.tsx` shows a validation toast, THE component SHALL use `t('validation.required', { field })` from the `members` namespace instead of hardcoded Dutch text
2. WHEN `UserModal.tsx` shows a validation toast, THE component SHALL use translated messages from the `members` namespace
3. WHEN `CsvUpload.tsx` shows a file type error toast, THE component SHALL use a translated message from the `members` namespace (e.g., `members:errors.invalid_file_type`)
4. WHEN `OrderItemFieldsEditor.tsx` produces validation errors, THE editor SHALL use the Validation_Helper with the `webshop` namespace `t` function for `required` and `unique` error messages

### Requirement 9: Migrate Event Module Validation

**User Story:** As a developer managing event files, I want validation messages to use i18n, so that file upload errors are translated.

#### Acceptance Criteria

1. WHEN `eventPosterUpload.ts` returns a validation error for invalid file type, THE service SHALL return a translation key (`events:validation.poster_invalid_type`) instead of a hardcoded Dutch string
2. WHEN `eventPosterUpload.ts` returns a validation error for file size, THE service SHALL return a translation key from the `events` namespace with interpolation for the size limit

### Requirement 10: Translation Key Consistency

**User Story:** As a developer, I want a predictable naming convention for validation keys within each domain namespace, so that new forms can follow the same pattern without confusion.

#### Acceptance Criteria

1. EACH Domain_Namespace validation keys SHALL follow the pattern: `{namespace}:validation.{rule_type}` (e.g., `products:validation.required`, `eventBooking:validation.email`, `members:validation.min_length`)
2. EACH Domain_Namespace error keys SHALL follow the pattern: `{namespace}:errors.{error_type}` for domain-specific error messages
3. EACH Domain_Namespace toast keys SHALL follow the pattern: `{namespace}:toast.{action_result}` for success/error toasts
4. THE Common_Namespace SHALL ONLY contain cross-cutting concerns: `common:errors.network`, `common:errors.unauthorized`, `common:errors.server_error`, `common:errors.maintenance`, `common:errors.timeout`, `common:errors.unknown`, `common:notifications.*`, and `common:api_errors.*`
5. THE Common_Namespace SHALL NOT contain any `validation.*` keys — those belong exclusively in domain namespaces
6. WHEN both `src/locales/` and `public/locales/` contain the same namespace file, THE translations SHALL be added to both locations in the same commit

### Requirement 11: Backward Compatibility

**User Story:** As a user, I want the application to continue working during the migration, so that partially-migrated forms still show meaningful error messages.

#### Acceptance Criteria

1. WHEN the Validation_Helper `t()` call fails to find a key, THE helper SHALL fall back to the `defaultValue` option with the original Dutch string
2. IF a module has not yet been migrated to use the Validation_Helper, THEN THE existing hardcoded messages SHALL continue to function until that module is migrated
3. THE Validation_Helper SHALL be additive — it SHALL NOT require all modules to migrate simultaneously

### Requirement 12: Backend Error_Key Adoption in Key Handlers

**User Story:** As a user, I want backend API errors to include `error_key` so that the frontend can display them in my language, even when the backend sends field-specific detail.

#### Acceptance Criteria

1. WHEN a backend handler calls `create_error_response(400, ...)` for a validation error, THE handler SHALL include `error_key='validation_error'` and `locale=locale` parameters
2. WHEN a backend handler calls `create_error_response` for permission/auth errors, THE handler SHALL include the appropriate `error_key` (`forbidden`, `authorization_required`)
3. THE backend handlers SHALL preserve the existing detailed `error` field (e.g., `"Missing required parameter: regio"`) alongside the localized `message` field — both are useful
4. THE backend handlers for `submit_order`, `update_order_items`, `update_product`, `update_event`, and `update_payment` SHALL adopt the `error_key` + `locale` pattern (currently only `update_member` uses it)
5. WHEN a backend handler resolves the locale, THE handler SHALL use `resolve_request_locale(event)` from `shared.i18n.locale_resolver`
