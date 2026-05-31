# Implementation Plan: Order Confirmation PDF

## Overview

Move order confirmation PDF generation from client-side jsPDF to a backend Lambda using WeasyPrint. The implementation follows the established handler pattern (auth layer, CORS, error responses) and the proven S3-images-in-PDF pattern (base64 data URIs). The frontend replaces the current HTML download workaround with a single API call that triggers a browser download.

## Tasks

- [x] 1. Create Lambda handler with validation and auth
  - [x] 1.1 Create `backend/handler/generate_order_pdf/app.py` with Lambda handler skeleton
    - Create directory and `__init__.py`
    - Import shared auth layer (`extract_user_credentials`, `validate_permissions_with_regions`, `cors_headers`, `handle_options_request`, `create_error_response`)
    - Handle OPTIONS preflight
    - Extract and validate `order_id` from `pathParameters` (return 400 if empty/whitespace)
    - Extract user credentials via auth layer (return 401/503 on failure)
    - Fetch order from DynamoDB Orders table (return 404 if not found)
    - Validate ownership: user email matches order `user_email` (case-insensitive) OR user has `products_create` permission (return 403 otherwise)
    - _Requirements: 1.1, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 1.2 Write property test for authorization logic
    - **Property 1: Authorization grants access if and only if user is owner or admin**
    - **Validates: Requirements 2.2, 2.3, 2.4**

  - [x] 1.3 Write property test for order_id validation
    - **Property 7: Invalid order_id rejection**
    - **Validates: Requirements 1.5**

- [x] 2. Implement logo fetching and HTML template rendering
  - [x] 2.1 Implement S3 logo fetch utility function in `app.py`
    - Create `fetch_logo_as_data_uri(bucket, key, timeout=5)` function
    - Use boto3 `get_object` to fetch image from `my-hdcn-bucket/imagesWebsite/hdcnFavico.png`
    - Read `ContentType` from S3 metadata, base64-encode body, construct data URI
    - Return `None` on any failure (ClientError, timeout, etc.) and log warning
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.2 Write property test for S3 image to data URI encoding
    - **Property 2: S3 image to data URI round-trip**
    - **Validates: Requirements 3.2**

  - [x] 2.3 Create HTML template and rendering function
    - Create `render_order_html(order, logo_data_uri)` function
    - HTML template with: header (logo + "H-DCN Webshop / Orderbevestiging"), order metadata (ordernummer, datum, status), customer address (name, straat, postcode, woonplaats, conditionally email/phone), product table (product, optie, aantal, prijs, totaal), delivery option row (if present), totals section (subtotaal, verzendkosten, totaal), footer
    - Use A4-appropriate CSS styling with `@page { size: A4; }`
    - Format monetary values with euro symbol and 2 decimal places (e.g., "€12.50")
    - Format date in Dutch locale: "15 januari 2025, 14:30"
    - Conditionally include logo `<img>` only when `logo_data_uri` is not None
    - Handle item name from either `name` or `naam` field; display "-" for missing `selectedOption`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 3.3_

  - [x] 2.4 Write property test for template data completeness
    - **Property 3: Template data completeness**
    - **Validates: Requirements 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7**

  - [x] 2.5 Write property test for monetary value formatting
    - **Property 4: Monetary value formatting**
    - **Validates: Requirements 4.8**

  - [x] 2.6 Write property test for Dutch locale date formatting
    - **Property 5: Dutch locale date formatting**
    - **Validates: Requirements 4.9**

- [x] 3. Implement WeasyPrint PDF rendering and wire handler together
  - [x] 3.1 Complete the Lambda handler with PDF generation
    - Call `fetch_logo_as_data_uri` to get logo
    - Call `render_order_html` with order data and logo URI
    - Render HTML to PDF using `weasyprint.HTML(string=html).write_pdf()`
    - Base64-encode PDF bytes for API Gateway binary response
    - Return response with `statusCode: 200`, `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="orderbevestiging-{order_id}.pdf"`, `isBase64Encoded: True`
    - Catch WeasyPrint rendering errors → return 500 with "PDF rendering failed"
    - _Requirements: 1.2, 1.3, 5.1, 5.2, 5.3, 5.4_

  - [x] 3.2 Write property test for valid PDF generation
    - **Property 6: Valid PDF generation for any order**
    - **Validates: Requirements 1.2, 1.3, 5.2**

  - [x] 3.3 Add `requirements.txt` for generate_order_pdf handler
    - Add `weasyprint` dependency
    - _Requirements: 5.1_

- [x] 4. Checkpoint - Ensure backend logic is correct
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. SAM template and IAM configuration
  - [x] 5.1 Add Lambda function and IAM role to `backend/template.yaml`
    - Add `GenerateOrderPdfFunction` resource (CodeUri: `handler/generate_order_pdf`, Handler: `app.lambda_handler`, Runtime: python3.11, Timeout: 30, MemorySize: 512)
    - Attach `AuthLayer` via Layers property
    - Add environment variables: `ORDERS_TABLE`, `S3_BUCKET`, `LOGO_S3_KEY`
    - Add API event: `GET /orders/{order_id}/pdf` on `MyApi`
    - Add `PdfGeneratorRole` IAM role with: `AWSLambdaBasicExecutionRole`, `AWSXRayDaemonWriteAccess`, DynamoDB GetItem/Query on Orders table + indexes, S3 GetObject on `my-hdcn-bucket/imagesWebsite/*`
    - Configure API Gateway binary media types for `application/pdf` if not already present
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 5.2 Create Dockerfile for Docker-based Lambda deployment
    - Create `backend/handler/generate_order_pdf/Dockerfile` based on `public.ecr.aws/lambda/python:3.11`
    - Install WeasyPrint system dependencies: pango, pango-devel, gdk-pixbuf2, cairo, cairo-gobject, gobject-introspection, libffi-devel
    - Copy shared auth layer from `layers/auth-layer/python/` into the image (Lambda Layers not supported with container images)
    - Copy `requirements.txt` and install Python dependencies
    - Copy handler code (`app.py`, `__init__.py`)
    - Set CMD to `app.lambda_handler`
    - _Requirements: 6.5, 6.6, 6.8, 6.9_

  - [x] 5.3 Update `template.yaml` to use Docker-based deployment
    - Change `GenerateOrderPdfFunction` from zip to container image (`PackageType: Image`)
    - Add `Metadata` block with `DockerTag`, `DockerContext: .`, `Dockerfile: handler/generate_order_pdf/Dockerfile`
    - Remove `CodeUri`, `Handler`, `Runtime`, and `Layers` properties (replaced by Docker image)
    - Keep `Role`, `Environment`, `Events`, `Timeout`, `MemorySize` properties
    - Validate template with `sam validate`
    - _Requirements: 6.1, 6.2, 6.5, 6.8, 6.9_

- [x] 6. Frontend PDF download integration
  - [x] 6.1 Create PDF download service in `frontend/src/modules/webshop/services/pdfDownloadService.ts`
    - Export `downloadOrderPdf(orderId: string)` function
    - Send authenticated GET request to `/orders/{order_id}/pdf` with `responseType: 'blob'`
    - On success: create Blob from response, generate object URL, trigger download with filename `orderbevestiging-{order_id}.pdf`
    - Return typed error information for 401, 403, 404, 500 status codes
    - Handle 30-second timeout
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 6.2 Add download PDF button to OrderConfirmation component
    - Add "Download PDF" button to `frontend/src/modules/webshop/components/OrderConfirmation.tsx`
    - Use Chakra UI Button component with download icon
    - Show loading spinner and disable button while request is in progress
    - Display error toast/message for auth errors (401/403), not found (404), and server errors (500/timeout)
    - Call `downloadOrderPdf` service on click
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 6.3 Write unit tests for PDF download service and button
    - Test API call with correct URL and auth headers
    - Test blob creation and download trigger on success
    - Test error message display for each error status
    - Test loading state management
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The backend follows the established handler pattern (shared auth layer, CORS, structured error responses)
- The S3 logo pattern follows the proven myadmin approach (base64 data URIs)
- WeasyPrint requires system-level dependencies (cairo, pango, etc.) — these are installed in the Docker image (tasks 5.2, 5.3)
- Lambda Layers are not compatible with container-based deployments — the auth layer is copied directly into the Docker image

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.2", "2.3"] },
    { "id": 2, "tasks": ["2.4", "2.5", "2.6", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "5.1"] },
    { "id": 4, "tasks": ["5.2"] },
    { "id": 5, "tasks": ["5.3"] },
    { "id": 6, "tasks": ["6.1"] },
    { "id": 7, "tasks": ["6.2"] },
    { "id": 8, "tasks": ["6.3"] }
  ]
}
```
