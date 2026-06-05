# Requirements Document

## Introduction

Multi-language support for the H-DCN (Harley-Davidson Club Nederland) member portal and webshop. The application currently serves content exclusively in Dutch. This feature introduces internationalization (i18n) to support eight European languages: Dutch (NL), English (GB), French (FR), German (DE), Swedish (SE), Danish (DK), Italian (IT), and Spanish (ES). Dutch remains the default and fallback language. The admin panel remains Dutch-only to reduce translation scope and because all administrators are Dutch-speaking.

## Glossary

- **I18n_System**: The internationalization infrastructure responsible for loading, resolving, and rendering translated content across frontend and backend
- **Language_Selector**: The UI component that allows users to choose their preferred display language
- **Translation_Store**: The structured collection of translation key-value pairs organized by locale and namespace
- **Locale_Resolver**: The component that determines which language to display based on user preference, stored setting, or browser default
- **Member_Profile**: The DynamoDB record for a club member, stored in the Members table
- **Email_Renderer**: The backend service that generates localized email content using language-specific templates
- **PDF_Generator**: The WeasyPrint-based backend service that produces order confirmation and membership documents
- **Supported_Locales**: The set of language codes supported by the system: nl, en, fr, de, sv, da, it, es
- **Fallback_Language**: Dutch (nl), used when a translation key is missing for the selected locale
- **Admin_Panel**: The administrative sections of the portal (member management, product management, event management, exports, membership management)

## Requirements

### Requirement 1: Frontend Internationalization Framework

**User Story:** As a developer, I want a structured i18n framework integrated into the React frontend, so that all user-facing text can be translated without code changes.

#### Acceptance Criteria

1. THE I18n_System SHALL use react-i18next as the frontend internationalization library
2. THE I18n_System SHALL organize translations into namespace files per feature module (common, dashboard, webshop, members, events, products, auth)
3. THE I18n_System SHALL load translation files from `frontend/src/locales/{locale}/{namespace}.json`
4. THE I18n_System SHALL support all eight Supported_Locales: nl, en, fr, de, sv, da, it, es
5. WHEN a translation key is missing for the selected locale, THE I18n_System SHALL fall back to the Dutch (nl) translation
6. WHEN a translation key is missing in both the selected locale and Dutch, THE I18n_System SHALL display the translation key itself as visible text
7. THE I18n_System SHALL lazy-load namespace translation files on demand when the corresponding feature module is rendered, rather than loading all namespaces at application startup
8. WHILE translation files for the active namespace are being loaded, THE I18n_System SHALL render an empty string for pending translation keys and prevent a flash of raw translation keys
9. THE I18n_System SHALL complete initialization of the common namespace and the active locale before rendering the application shell, using React Suspense or an equivalent loading boundary to block rendering until ready

### Requirement 2: Language Preference Storage and Resolution

**User Story:** As a member, I want my language preference to persist across sessions, so that I do not have to select my language every time I visit the portal.

#### Acceptance Criteria

1. THE Locale_Resolver SHALL determine the active language using the following priority order: stored user preference, browser locale, Dutch default
2. WHEN a member is authenticated, THE Locale_Resolver SHALL read the language preference from the Member_Profile `preferred_language` attribute in DynamoDB
3. WHEN a member has no stored language preference, THE Locale_Resolver SHALL detect the browser language using `navigator.language` and match the primary language subtag (e.g., "en" from "en-US") against Supported_Locales
4. IF the detected browser language's primary subtag is not in Supported_Locales, THEN THE Locale_Resolver SHALL default to Dutch (nl)
5. IF the stored `preferred_language` value is not in Supported_Locales, THEN THE Locale_Resolver SHALL treat it as absent and fall through to browser locale detection
6. WHEN a member changes their language preference, THE I18n_System SHALL persist the selection to the Member_Profile `preferred_language` attribute via the existing update member API
7. IF the language preference persistence API call fails, THEN THE I18n_System SHALL apply the new language locally for the current session and display an error message indicating the preference could not be saved
8. WHEN a member changes their language preference, THE I18n_System SHALL apply the new language to all displayed text within 1 second without requiring a page reload

### Requirement 3: Language Selector Component

**User Story:** As a member, I want a visible language selector in the portal navigation, so that I can switch the display language at any time.

#### Acceptance Criteria

1. THE Language_Selector SHALL be displayed in the navigation header on all member-facing pages, and SHALL be hidden on Admin_Panel pages
2. THE Language_Selector SHALL display all eight Supported_Locales as options, each showing a country flag icon and the native language name (e.g., "Nederlands", "English", "Français", "Deutsch", "Svenska", "Dansk", "Italiano", "Español")
3. THE Language_Selector SHALL indicate the currently active language by displaying the active language's flag and name in its collapsed state, and by visually distinguishing the active language from other options in its expanded state
4. WHEN a user selects a language, THE Language_Selector SHALL apply the new language to all visible member-facing text within 1 second without requiring a page reload
5. THE Language_Selector SHALL be accessible via keyboard navigation and meet WCAG 2.1 AA contrast requirements (minimum 4.5:1 ratio for text, 3:1 for graphical elements)
6. IF the language preference fails to persist to the Member_Profile, THEN THE Language_Selector SHALL still apply the selected language locally for the current session and display a non-blocking notification indicating the preference was not saved

### Requirement 4: Frontend Text Extraction and Translation

**User Story:** As a member, I want all user-facing text displayed in my chosen language, so that I can use the portal comfortably in my native language.

#### Acceptance Criteria

1. THE I18n_System SHALL externalize all hardcoded Dutch text strings from member-facing React components into translation files, excluding Admin_Panel pages which remain Dutch-only per Requirement 9
2. THE I18n_System SHALL translate the following text categories: page headings, button labels, form labels, form placeholder text, validation messages, status messages, navigation items, card descriptions, tooltip text, modal titles, table column headers, and confirmation dialogs
3. THE I18n_System SHALL support interpolation for dynamic values within translated strings using the i18next interpolation syntax (e.g., member names, dates, counts)
4. THE I18n_System SHALL handle plural forms for each Supported_Locale according to the CLDR plural rules supported by the i18next pluralization system
5. IF a translation namespace file fails to load for the selected locale, THEN THE I18n_System SHALL fall back to the Dutch (nl) namespace file and display content in Dutch rather than showing empty text or translation keys
6. THE I18n_System SHALL not translate proper nouns, brand names (e.g., "H-DCN", "Harley-Davidson"), or user-generated content stored in the database

### Requirement 5: Date, Number, and Currency Formatting

**User Story:** As a member, I want dates, numbers, and currency values formatted according to my locale conventions, so that information is familiar and readable.

#### Acceptance Criteria

1. WHEN displaying dates, THE I18n_System SHALL format dates using the Intl.DateTimeFormat API with the active locale, applying the "short" date style (e.g., "31-12-2024" for nl, "12/31/2024" for en) for tabular displays and "long" date style (e.g., "31 december 2024" for nl, "December 31, 2024" for en) for detail views and headings
2. WHEN displaying currency values, THE I18n_System SHALL format amounts using EUR as the currency code with exactly 2 decimal places, applying locale-appropriate decimal separators, thousands grouping, and Euro symbol placement via the Intl.NumberFormat API
3. WHEN displaying numeric values, THE I18n_System SHALL use the Intl.NumberFormat API with the active locale to apply locale-appropriate decimal separators and thousands grouping
4. THE I18n_System SHALL use the Intl.DateTimeFormat and Intl.NumberFormat browser APIs for locale-aware formatting, passing the active locale code from the Locale_Resolver as the locale argument
5. IF a date, number, or currency value is null, undefined, or not parseable, THEN THE I18n_System SHALL display an empty string and not render an error or fallback text to the user

### Requirement 6: Backend API Error Messages

**User Story:** As a member, I want API error messages displayed in my chosen language, so that I can understand what went wrong without needing to translate Dutch error text.

#### Acceptance Criteria

1. WHEN the frontend sends an API request, THE I18n_System SHALL include the active locale as a Supported_Locales code (nl, en, fr, de, sv, da, it, es) in the `Accept-Language` HTTP header
2. WHEN the backend returns an error response to the frontend, THE I18n_System SHALL include both a stable error key for programmatic use and a localized human-readable message based on the `Accept-Language` header value
3. IF the `Accept-Language` header is missing or contains a locale not in Supported_Locales, THEN THE I18n_System SHALL treat the locale as Dutch (nl) for error message resolution
4. IF the requested locale is not available for a specific error message, THEN THE I18n_System SHALL return the Dutch (nl) error message as fallback
5. THE I18n_System SHALL maintain error message translation files in the backend shared layer at `backend/layers/auth-layer/python/shared/i18n/`

### Requirement 7: Email Template Localization

**User Story:** As a member, I want emails from H-DCN sent in my preferred language, so that I can understand membership communications without translation.

#### Acceptance Criteria

1. WHEN sending a transactional email to a member, THE Email_Renderer SHALL use the member's `preferred_language` attribute to select the email template language
2. IF the member's `preferred_language` attribute is empty, null, or not a valid Supported_Locale, THEN THE Email_Renderer SHALL use Dutch (nl) as the template language
3. THE Email_Renderer SHALL maintain separate HTML template files for each Supported_Locale in `backend/email-templates/templates/{locale}/`
4. WHEN a template does not exist for the member's preferred language, THE Email_Renderer SHALL use the Dutch template as fallback
5. THE Email_Renderer SHALL localize all static text content within email templates including subject lines, greetings, instructions, and footer text
6. THE Email_Renderer SHALL format dates and currency values within emails according to the member's preferred locale using locale-appropriate date patterns (e.g., dd-MM-yyyy for nl, MM/dd/yyyy for en) and Euro currency formatting with locale-specific decimal and thousands separators

### Requirement 8: Order PDF Localization

**User Story:** As a member, I want order confirmation PDFs generated in my preferred language, so that I have clear documentation of my purchases.

#### Acceptance Criteria

1. WHEN generating an order confirmation PDF, THE PDF_Generator SHALL retrieve the ordering member's `preferred_language` from the Members table using the `member_id` stored on the order record
2. THE PDF_Generator SHALL translate all static text in the PDF according to the resolved document language, including: the document title, section headings (addresses, delivery, products), table column headers, field labels (order number, date, customer, status), status values, totals labels, and fallback text for missing data
3. THE PDF_Generator SHALL format dates according to the resolved locale convention (e.g., "15 januari 2025" for Dutch, "15 January 2025" for English, "15. Januar 2025" for German) and format currency amounts using the Euro symbol with locale-appropriate decimal and thousands separators
4. IF the member's `preferred_language` is not one of the eight Supported_Locales (nl, en, fr, de, sv, da, it, es) or is null or empty, THEN THE PDF_Generator SHALL generate the PDF in Dutch (nl) as the fallback language
5. THE PDF_Generator SHALL maintain translation key-value mappings for PDF static text for each of the eight Supported_Locales in the backend shared layer

### Requirement 9: Admin Panel Language Scope

**User Story:** As an administrator, I want the admin panel to remain in Dutch, so that the translation effort is focused on member-facing content and administrative workflows remain consistent.

#### Acceptance Criteria

1. THE I18n_System SHALL keep all Admin_Panel pages in Dutch regardless of the user's language preference
2. THE I18n_System SHALL define admin-specific translation namespaces that only contain Dutch translations
3. WHEN a user navigates from a member-facing page to an Admin_Panel page, THE I18n_System SHALL switch the displayed language to Dutch without requiring a page reload
4. WHEN a user navigates from an Admin_Panel page to a member-facing page, THE I18n_System SHALL restore the user's preferred language without requiring a page reload
5. WHILE an Admin_Panel page is active, THE I18n_System SHALL hide the Language_Selector component since language selection has no effect on admin pages
6. WHILE an Admin_Panel page is active, THE I18n_System SHALL display shared UI components (navigation header, footer) in Dutch

### Requirement 10: Translation File Management

**User Story:** As a developer, I want a structured and maintainable translation file system, so that translations can be added and updated efficiently.

#### Acceptance Criteria

1. THE Translation_Store SHALL use JSON format with UTF-8 encoding for all frontend translation files
2. THE Translation_Store SHALL use a maximum nesting depth of two object levels within each namespace file, where level one is a grouping key and level two contains the translated string values (e.g., `{"form": {"submitLabel": "Opslaan"}}`)
3. THE Translation*Store SHALL use lowercase dot-notation keys containing only lowercase alphanumeric characters, dots, and underscores (matching pattern `^[a-z]a-z0-9*.]\*[a-z0-9]$`)
4. THE Translation_Store SHALL include the Dutch (nl) locale as the reference translation containing all keys, and every namespace file for Dutch SHALL contain at minimum one key-value pair
5. IF a translation file for a non-Dutch locale is missing one or more keys present in the Dutch reference, THEN THE I18n_System SHALL output a warning to the browser developer console during local development (`npm start`) identifying the locale, namespace, and each missing key name
6. IF a translation value in any locale file is an empty string, THEN THE I18n_System SHALL treat that key as missing and apply the Dutch fallback

### Requirement 11: Authentication Flow Localization

**User Story:** As a new or returning member, I want the login and signup flow displayed in my preferred language, so that I can authenticate without language barriers.

#### Acceptance Criteria

1. WHEN displaying the authentication screen, THE I18n_System SHALL detect the browser language using `navigator.language` and, if the detected language is in Supported_Locales, display the authentication UI in that language
2. IF the browser language detected on the authentication screen is not in Supported_Locales, THEN THE I18n_System SHALL display the authentication UI in Dutch (nl)
3. THE I18n_System SHALL translate all custom authentication UI text including login prompts, error messages, passkey instructions, and email verification messages into all Supported_Locales
4. WHEN a Cognito custom message trigger sends a verification code or welcome email, THE Email_Renderer SHALL use the browser locale passed through the client metadata to determine the email language
5. IF the client metadata does not contain a locale value or contains a locale not in Supported_Locales, THEN THE Email_Renderer SHALL generate the Cognito email in Dutch (nl)
