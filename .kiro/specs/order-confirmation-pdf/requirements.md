# Requirements Document

## Introduction

This feature moves order confirmation PDF generation from the client-side (jsPDF) to the backend (AWS Lambda) using WeasyPrint. The backend Lambda fetches the H-DCN logo from S3, base64-encodes it as a data URI, injects it into an HTML template, and renders the HTML to PDF using WeasyPrint. The frontend calls a new API endpoint to retrieve the generated PDF. This approach produces high-quality PDFs with proper image support, matching the proven pattern from the myadmin project.

## Glossary

- **PDF_Generator_Lambda**: The AWS Lambda function responsible for generating order confirmation PDFs server-side using WeasyPrint
- **WeasyPrint**: A Python library that renders HTML/CSS to PDF documents
- **Data_URI**: A base64-encoded inline representation of binary data (e.g., `data:image/png;base64,...`) embedded directly in HTML
- **Order_Confirmation_Template**: The HTML template used to render the order confirmation, containing placeholders for order data and images
- **S3_Logo**: The H-DCN organization logo stored in the S3 bucket (`my-hdcn-bucket`) used as the header image in the PDF
- **Frontend_Client**: The React webshop frontend application that requests PDF generation from the backend API
- **Orders_Table**: The DynamoDB table storing order records
- **API_Gateway**: The AWS API Gateway (MyApi) that routes HTTP requests to Lambda functions

## Requirements

### Requirement 1: PDF Generation API Endpoint

**User Story:** As a webshop customer, I want to download a PDF order confirmation, so that I have a professional document for my records.

#### Acceptance Criteria

1. WHEN the Frontend_Client sends a GET request to `/orders/{order_id}/pdf`, THE API_Gateway SHALL route the request to the PDF_Generator_Lambda
2. WHEN the PDF_Generator_Lambda receives an order_id that exists in the Orders_Table, THE PDF_Generator_Lambda SHALL return HTTP 200 with a PDF document with Content-Type `application/pdf`
3. WHEN the PDF_Generator_Lambda receives an order_id that exists in the Orders_Table, THE PDF_Generator_Lambda SHALL include the header `Content-Disposition: attachment; filename="orderbevestiging-{order_id}.pdf"`
4. IF the order_id does not exist in the Orders_Table, THEN THE PDF_Generator_Lambda SHALL return HTTP 404 with an error message indicating the order was not found
5. IF the order_id is not a valid non-empty string, THEN THE PDF_Generator_Lambda SHALL return HTTP 400 with an error message indicating the order_id format is invalid

### Requirement 2: Authentication and Authorization

**User Story:** As a system administrator, I want PDF generation to be protected by authentication, so that only authorized users can access order confirmations.

#### Acceptance Criteria

1. IF the request does not contain a valid Authorization header with a Bearer token containing a well-formed JWT, THEN THE PDF_Generator_Lambda SHALL return HTTP 401 with an error message indicating the authentication failure reason
2. WHEN an authenticated user requests a PDF for an order whose associated email address matches the email in the user's JWT token, THE PDF_Generator_Lambda SHALL generate and return the PDF
3. WHEN an authenticated user with the `products_create` permission (granted by `Products_CRUD`, `Webshop_Management`, or `System_CRUD` roles) requests a PDF for any order, THE PDF_Generator_Lambda SHALL generate and return the PDF regardless of order ownership
4. IF an authenticated user requests a PDF for an order whose associated email address does not match the user's JWT email and the user does not have the `products_create` permission, THEN THE PDF_Generator_Lambda SHALL return HTTP 403 with an error message indicating insufficient permissions
5. IF the authentication system encounters an internal error while validating credentials, THEN THE PDF_Generator_Lambda SHALL return HTTP 503 with an error message indicating temporary unavailability

### Requirement 3: Logo Retrieval from S3

**User Story:** As a webshop owner, I want the organization logo to appear in the PDF, so that the order confirmation looks professional and branded.

#### Acceptance Criteria

1. WHEN the PDF_Generator_Lambda generates a PDF, THE PDF_Generator_Lambda SHALL fetch the H-DCN logo from the S3 object key `imagesWebsite/hdcnFavico.png` in `my-hdcn-bucket` with a timeout of 5 seconds
2. WHEN the logo is fetched from S3, THE PDF_Generator_Lambda SHALL read the content type from the S3 object metadata, base64-encode the image binary content, and construct a Data_URI using the format `data:{content_type};base64,{encoded_data}`
3. THE PDF_Generator_Lambda SHALL inject the Data_URI into the Order_Confirmation_Template as the `src` attribute of the logo `<img>` element
4. IF the logo cannot be fetched from S3 due to a missing object, access denied error, network timeout, or any other S3 retrieval failure, THEN THE PDF_Generator_Lambda SHALL omit the logo `<img>` element from the rendered template, generate the PDF without it, and log a warning that includes the failure reason

### Requirement 4: HTML Template Rendering

**User Story:** As a webshop customer, I want the PDF to contain all my order details in a clear layout, so that I can easily review my purchase.

#### Acceptance Criteria

1. THE Order_Confirmation_Template SHALL include the order number, order date, and payment status
2. THE Order_Confirmation_Template SHALL include customer information: name, street address, postal code, and city
3. IF the order contains a customer email address, THEN THE Order_Confirmation_Template SHALL display the customer email address in the customer information section
4. IF the order contains a customer phone number, THEN THE Order_Confirmation_Template SHALL display the customer phone number in the customer information section
5. THE Order_Confirmation_Template SHALL include a product table with columns: product name, option (displaying "-" when no option is selected), quantity, unit price, and line total where line total equals quantity multiplied by unit price
6. THE Order_Confirmation_Template SHALL include the subtotal and total amount
7. IF a delivery option is present in the order, THEN THE Order_Confirmation_Template SHALL display the delivery option label and delivery cost, and include the delivery cost in the totals section
8. WHEN the PDF_Generator_Lambda renders the template, THE PDF_Generator_Lambda SHALL format all monetary values (unit price, line total, subtotal, delivery cost, and total amount) with the euro symbol prefix and exactly two decimal places (e.g., "€12.50")
9. WHEN the PDF_Generator_Lambda renders the template, THE PDF_Generator_Lambda SHALL format the order date in Dutch locale with day, full month name, year, hours, and minutes (e.g., "15 januari 2025, 14:30")

### Requirement 5: WeasyPrint PDF Rendering

**User Story:** As a developer, I want the PDF to be rendered using WeasyPrint, so that the output is a high-quality PDF with proper CSS support.

#### Acceptance Criteria

1. WHEN the Order_Confirmation_Template is populated with order data and the logo Data_URI, THE PDF_Generator_Lambda SHALL pass the complete HTML string to WeasyPrint for PDF rendering
2. THE PDF_Generator_Lambda SHALL produce a valid PDF document that starts with the `%PDF` header, has non-zero byte size, and contains at least one page
3. THE PDF_Generator_Lambda SHALL render the PDF using A4 page size (210mm × 297mm), consistent with Dutch business document standards
4. IF WeasyPrint encounters a rendering error, THEN THE PDF_Generator_Lambda SHALL return HTTP 500 with an error message indicating a rendering failure and log the error details including the exception type and message

### Requirement 6: Lambda Deployment Configuration

**User Story:** As a DevOps engineer, I want the PDF generation Lambda to be properly configured, so that it has sufficient resources for WeasyPrint rendering.

#### Acceptance Criteria

1. THE PDF_Generator_Lambda SHALL be configured with a memory allocation of 512 MB to accommodate WeasyPrint rendering
2. THE PDF_Generator_Lambda SHALL be configured with a timeout of 30 seconds to allow for S3 image fetching and PDF rendering
3. THE PDF_Generator_Lambda SHALL have IAM permissions to perform s3:GetObject on objects within the `my-hdcn-bucket` bucket
4. THE PDF_Generator_Lambda SHALL have IAM permissions to perform dynamodb:GetItem and dynamodb:Query on the Orders_Table and its indexes
5. THE PDF_Generator_Lambda SHALL include the shared authentication layer code (AuthLayer) within its container image, since Lambda Layers are not compatible with container-based deployments
6. THE PDF_Generator_Lambda SHALL use the python3.11 runtime, consistent with other Lambda functions in the stack
7. IF the PDF_Generator_Lambda invocation exceeds the 30-second timeout, THEN THE PDF_Generator_Lambda SHALL terminate execution and return a timeout error to the caller
8. THE PDF_Generator_Lambda SHALL be deployed as a container image (PackageType: Image) that includes all WeasyPrint system-level dependencies (cairo, pango, gdk-pixbuf, gobject-introspection, libffi) pre-installed in the image
9. THE PDF_Generator_Lambda container image SHALL be built from the official AWS Lambda Python 3.11 base image (`public.ecr.aws/lambda/python:3.11`) to ensure compatibility with the Lambda runtime environment

### Requirement 7: Frontend Integration

**User Story:** As a webshop customer, I want to click a button to download my order confirmation as PDF, so that I can save or print it easily.

#### Acceptance Criteria

1. WHEN the user clicks the download PDF button on the order confirmation page, THE Frontend_Client SHALL send an authenticated GET request to `/orders/{order_id}/pdf` with response type set to binary blob
2. WHEN the Frontend_Client receives a successful PDF response, THE Frontend_Client SHALL trigger a browser download with filename `orderbevestiging-{order_id}.pdf`
3. IF the Frontend_Client receives an HTTP 401 or 403 error response, THEN THE Frontend_Client SHALL display an error message indicating the user is not authorized to download this PDF
4. IF the Frontend_Client receives an HTTP 404 error response, THEN THE Frontend_Client SHALL display an error message indicating the order was not found
5. IF the Frontend_Client receives an HTTP 500 error response or the request exceeds 30 seconds without a response, THEN THE Frontend_Client SHALL display an error message indicating the PDF could not be generated and the user should try again
6. WHILE the PDF is being generated, THE Frontend_Client SHALL display a loading indicator and disable the download PDF button to prevent duplicate requests
