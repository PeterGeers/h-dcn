# Requirements Document

## Introduction

This document specifies the requirements for completing the financial field standardization across the H-DCN portal. The goal is to eliminate runtime crashes (`toFixed is not a function`) and inconsistent price display by: replacing remaining inline formatting patterns with safe helpers, adding backend validation that rejects non-numeric prices, adding a steering rule for future enforcement, and migrating existing string-typed prices to DynamoDB Number type.

## Glossary

- **System**: The H-DCN portal application (frontend + backend + data layer)
- **Frontend**: React TypeScript SPA at `frontend/src/`
- **Backend_Handler**: A Lambda function handler at `backend/handler/<name>/app.py`
- **Migration_Script**: A one-time Python script at `scripts/migrate_price_fields_to_number.py`
- **Steering_Rule**: A documented enforcement rule in `.kiro/steering/schema-driven.md`
- **Price_Field**: Any DynamoDB attribute storing a monetary value (prijs, price, unit_price, line_total, total_amount)
- **formatPrice**: Helper function at `frontend/src/utils/formatPrice.ts` that safely formats any value to `€X.XX`
- **toPrice**: Helper function at `frontend/src/utils/formatPrice.ts` that safely converts any value to a finite number
- **validate_price_field**: Shared Python function that validates and coerces price values to Decimal

## Requirements

### Requirement 1: Frontend inline price pattern elimination

**User Story:** As a user, I want prices to always display correctly, so that I never see crashes or inconsistent formatting when browsing the webshop.

#### Acceptance Criteria

1. WHEN WebshopPage renders a product price, THE Frontend SHALL use `formatPrice(item.price)` instead of inline `Number(item.price || 0).toFixed(2)`
2. WHEN CheckoutModal renders a line total, THE Frontend SHALL use `formatPrice(toPrice(item.price) * item.quantity)` instead of inline arithmetic with `.toFixed(2)`
3. WHEN OrderConfirmation renders item prices, THE Frontend SHALL use `formatPrice(item.price)` instead of inline `Number(item.price || 0).toFixed(2)`
4. WHEN AdvancedExportsPage renders average price statistics, THE Frontend SHALL use `formatPrice(productStats.gemiddeldePrijs)` instead of inline `.toFixed(2)`
5. WHEN any replaced component receives a null, undefined, or non-numeric price value, THE Frontend SHALL display `€0.00` without throwing an error

### Requirement 2: Backend price validation shared helper

**User Story:** As a developer, I want a shared validation function for price fields, so that all handlers enforce numeric types consistently without duplicating logic.

#### Acceptance Criteria

1. THE validate_price_field function SHALL accept int, float, Decimal, and numeric string values and return a valid Decimal
2. THE validate_price_field function SHALL reject non-numeric strings, empty strings, booleans, lists, and dicts with a descriptive error message
3. WHEN validate_price_field receives None, THE function SHALL return (None, None) indicating the field is optional and absent
4. WHEN validate_price_field receives a valid numeric string, THE function SHALL coerce it to Decimal without precision loss
5. THE validate_price_field function SHALL never return NaN or Infinity as a valid Decimal value

### Requirement 3: Backend handler integration

**User Story:** As a system administrator, I want all price-writing API endpoints to reject invalid price values, so that only numeric prices are stored in DynamoDB.

#### Acceptance Criteria

1. WHEN admin_update_product receives a non-numeric `prijs` value, THE Backend_Handler SHALL return HTTP 400 with a descriptive error message
2. WHEN admin_create_variant receives a non-numeric `prijs` value, THE Backend_Handler SHALL return HTTP 400 with a descriptive error message
3. WHEN admin_create_product receives a non-numeric price value, THE Backend_Handler SHALL return HTTP 400 with a descriptive error message
4. WHEN create_order receives a non-numeric price in line items, THE Backend_Handler SHALL return HTTP 400 with a descriptive error message
5. WHEN any handler receives a valid numeric price, THE Backend_Handler SHALL store it as DynamoDB Number type (Decimal)

### Requirement 4: DynamoDB migration script

**User Story:** As a system administrator, I want to convert existing string-typed prices to Number type, so that all historical data is consistent with the new validation rules.

#### Acceptance Criteria

1. WHEN the Migration_Script runs with `--dry-run`, THE script SHALL log all records that would be converted without modifying any data
2. WHEN the Migration_Script runs without `--dry-run`, THE script SHALL convert string-typed price fields to DynamoDB Number type in the Producten table
3. WHEN the Migration_Script runs without `--dry-run`, THE script SHALL convert string-typed price fields in Orders table line items to DynamoDB Number type
4. WHEN the Migration_Script encounters a non-parseable string price, THE script SHALL log the error and skip that record without aborting
5. WHEN the Producten table contains more than 1MB of data, THE Migration_Script SHALL handle pagination via LastEvaluatedKey
6. THE Migration_Script SHALL support a `--profile` flag defaulting to `nonprofit-deploy`
7. THE Migration_Script SHALL log summary counts: scanned, converted, skipped, errors

### Requirement 5: Steering rule for future enforcement

**User Story:** As a developer, I want a documented rule enforcing DynamoDB Number type for financial fields, so that future code changes do not reintroduce string-typed prices.

#### Acceptance Criteria

1. THE Steering_Rule SHALL be added as section 6 in `.kiro/steering/schema-driven.md`
2. THE Steering_Rule SHALL list all financial field names that must use Number type (prijs, price, unit_price, line_total, total_amount, total_paid, purchase_price_per_unit)
3. THE Steering_Rule SHALL specify that backend handlers must coerce string prices to Decimal before writing
4. THE Steering_Rule SHALL specify that backend handlers must reject non-numeric values with HTTP 400

### Requirement 6: Property tests for validate_price_field

**User Story:** As a developer, I want property-based tests for the validation helper, so that I have confidence it handles all input types correctly across a wide range of values.

#### Acceptance Criteria

1. FOR ALL valid numeric inputs (int, float, Decimal, numeric string), THE property test SHALL verify that validate_price_field returns a Decimal equal in value to the input
2. FOR ALL non-numeric strings, THE property test SHALL verify that validate_price_field returns an error message
3. FOR ALL valid numeric strings x, THE property test SHALL verify that `validate_price_field(str(Decimal(x)))` produces the same Decimal as `validate_price_field(x)` (round-trip)
4. THE property tests SHALL use the hypothesis library with at least 100 examples per property

### Requirement 7: Unit tests for handler validation

**User Story:** As a developer, I want unit tests proving each handler rejects invalid prices and stores valid ones correctly, so that regressions are caught immediately.

#### Acceptance Criteria

1. WHEN tested with a non-numeric price, THE admin_update_product handler test SHALL verify a 400 response is returned
2. WHEN tested with a valid numeric price, THE admin_update_product handler test SHALL verify the price is stored as Decimal in DynamoDB
3. WHEN tested with a non-numeric price, THE admin_create_variant handler test SHALL verify a 400 response is returned
4. WHEN tested with a non-numeric price, THE admin_create_product handler test SHALL verify a 400 response is returned
5. WHEN tested with a non-numeric price in line items, THE create_order handler test SHALL verify a 400 response is returned
