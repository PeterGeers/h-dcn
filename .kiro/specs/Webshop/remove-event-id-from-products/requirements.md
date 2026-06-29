# Requirements Document

## Introduction

Remove `event_id` and `event_ids` fields from the Product domain entirely. The `event.product_ids[]` array becomes the single source of truth for associating products with events. This eliminates dual-source-of-truth conflicts and simplifies the data model.

## Glossary

- **Product_System**: The backend handlers and frontend components that manage product records in the Producten DynamoDB table
- **Field_Registry**: The product field configuration at `frontend/src/config/productFields/fields.ts` that defines available product fields
- **Product_Interface**: The TypeScript `Product` interface in `eventBooking.types.ts`
- **Admin_Product_Form**: The ProductCard component used by administrators to create and edit products
- **Get_Products_Handler**: The `get_products` Lambda handler that retrieves product records
- **Scan_Product_Handler**: The `scan_product` Lambda handler that returns product listings
- **Create_Product_Handler**: The `admin_create_product` Lambda handler
- **Update_Product_Handler**: The `admin_update_product` Lambda handler
- **Preparation_PDF_Generator**: The `generate_preparation_pdf` Lambda handler
- **Migration_Script**: A one-time Python script that removes deprecated attributes from DynamoDB records
- **Event_Product_IDs**: The `product_ids` array field on Event records that defines which products belong to an event

## Requirements

### Requirement 1: Remove event_id from Field Registry

**User Story:** As a developer, I want `event_id` and `event_ids` removed from the product field registry, so that no part of the system treats these as valid product attributes.

#### Acceptance Criteria

1. WHEN the Field_Registry is loaded, THE Product_System SHALL NOT include field definitions for `event_id` or `event_ids`
2. THE Field_Registry SHALL continue to define all other existing product fields without modification

### Requirement 2: Remove event_id from TypeScript Product Interface

**User Story:** As a developer, I want the Product TypeScript interface to not include `event_id` or `event_ids`, so that compile-time type checking prevents accidental use of these fields.

#### Acceptance Criteria

1. THE Product_Interface SHALL NOT contain `event_id` or `event_ids` properties
2. WHEN TypeScript compilation runs, THE Product_System SHALL produce zero type errors related to the removal of `event_id` and `event_ids`

### Requirement 3: Remove event_id from Product Creation

**User Story:** As a developer, I want the create product handler to stop accepting `event_id`, so that new products cannot be tagged with an event directly.

#### Acceptance Criteria

1. WHEN the Create_Product_Handler receives a request body containing `event_id`, THE Create_Product_Handler SHALL ignore the `event_id` field and not persist it to DynamoDB
2. WHEN the Create_Product_Handler receives a request body containing `event_ids`, THE Create_Product_Handler SHALL ignore the `event_ids` field and not persist it to DynamoDB
3. THE Create_Product_Handler SHALL continue to create product records with all other valid fields

### Requirement 4: Remove event_id from Product Update

**User Story:** As a developer, I want the update product handler to stop accepting `event_id`, so that existing products cannot have this field set or modified.

#### Acceptance Criteria

1. THE Update_Product_Handler SHALL NOT include `event_id` in its UPDATABLE_FIELDS list
2. THE Update_Product_Handler SHALL NOT include `event_ids` in its UPDATABLE_FIELDS list
3. WHEN the Update_Product_Handler receives a request body containing `event_id` or `event_ids`, THE Update_Product_Handler SHALL ignore those fields during the update operation

### Requirement 5: Remove Event Selector from Admin Product Form

**User Story:** As an administrator, I want the product edit form to not show an event selector, so that I manage event-product associations only from the Event form.

#### Acceptance Criteria

1. THE Admin_Product_Form SHALL NOT render an event selection input for `event_id`
2. THE Admin_Product_Form SHALL NOT render an event selection input for `event_ids`
3. THE Admin_Product_Form SHALL continue to render all other product fields without modification

### Requirement 6: Convert get_products to Batch-Get-by-IDs

**User Story:** As a developer, I want `get_products` to accept a list of product IDs and return those specific products, so that callers fetch products by explicit ID rather than scanning by event_id.

#### Acceptance Criteria

1. WHEN the Get_Products_Handler receives a `product_ids` parameter containing a list of product IDs, THE Get_Products_Handler SHALL return the product records matching those IDs using a DynamoDB batch-get operation
2. THE Get_Products_Handler SHALL NOT accept an `event_id` query parameter for filtering products
3. IF the Get_Products_Handler receives an empty `product_ids` list, THEN THE Get_Products_Handler SHALL return an empty product list with a 200 status code
4. IF any product ID in the `product_ids` list does not exist in DynamoDB, THEN THE Get_Products_Handler SHALL return the existing products and omit the missing IDs without error

### Requirement 7: Update Preparation PDF Generation

**User Story:** As a developer, I want the preparation PDF generator to fetch products via `event.product_ids` and batch-get, so that it no longer depends on scanning by `event_id`.

#### Acceptance Criteria

1. WHEN the Preparation_PDF_Generator generates a PDF for an event, THE Preparation_PDF_Generator SHALL retrieve the event's Event_Product_IDs array and use batch-get to fetch the associated products
2. THE Preparation_PDF_Generator SHALL NOT scan the Producten table using an `event_id` filter
3. IF the event has an empty Event_Product_IDs array, THEN THE Preparation_PDF_Generator SHALL generate the PDF without product data

### Requirement 8: Migration Script for DynamoDB Cleanup

**User Story:** As a developer, I want a migration script that removes `event_id` and `event_ids` attributes from all product records, so that legacy data is cleaned up.

#### Acceptance Criteria

1. WHEN the Migration_Script is executed with `--dry-run`, THE Migration_Script SHALL log which product records contain `event_id` or `event_ids` attributes without modifying any data
2. WHEN the Migration_Script is executed without `--dry-run`, THE Migration_Script SHALL remove `event_id` and `event_ids` attributes from all product records in the Producten DynamoDB table
3. THE Migration_Script SHALL support a `--profile` parameter with default value `nonprofit-deploy`
4. THE Migration_Script SHALL handle DynamoDB pagination to process all records regardless of table size
5. THE Migration_Script SHALL log the count of records processed and records modified

### Requirement 9: Remove event_id from Scan Product Response

**User Story:** As a developer, I want the scan product response to exclude `event_id`, so that API consumers do not receive deprecated fields.

#### Acceptance Criteria

1. WHEN the Scan_Product_Handler returns product records, THE Scan_Product_Handler SHALL NOT include `event_id` in the response body
2. WHEN the Scan_Product_Handler returns product records, THE Scan_Product_Handler SHALL NOT include `event_ids` in the response body

### Requirement 10: Remove Event Filter from Product Admin UI

**User Story:** As an administrator, I want the product admin page to not show an event filter dropdown, so that filtering by event is no longer possible in the product list view.

#### Acceptance Criteria

1. THE Product_System SHALL NOT render an event filter dropdown in the product admin list view
2. THE Product_System SHALL remove the useEventFilter hook usage from the product admin module
3. THE Product_System SHALL continue to display all other existing product list filters without modification
