# Requirements Document

## Introduction

This feature adds a clickable club logo next to the "Presidents' Meeting Booking" heading on the PresMeet booking page. Clicking the logo opens a file upload dialog allowing the user to replace their club's logo. The uploaded image is resized to a consistent thumbnail size and stored in S3, overwriting the previous logo. A cache-busting mechanism ensures the updated logo displays immediately after upload.

## Glossary

- **Logo_Uploader**: The frontend component that renders the club logo image and handles the click-to-upload interaction
- **Upload_Endpoint**: The backend Lambda function that receives the logo image, resizes it, and stores it in S3
- **Club_Logo**: A PNG image file stored at `assets/presmeet/logos/{club_id}.png` in the frontend S3 bucket
- **Frontend_Bucket**: The S3 bucket `h-dcn-frontend-506221081911` that serves the portal's static assets via CloudFront
- **Club_ID**: The unique identifier for a club, obtained from the authenticated user's Member record
- **Image_Resizer**: The server-side component (Pillow library in Lambda) that normalizes uploaded images to 200×200 pixels

## Requirements

### Requirement 1: Display Club Logo

**User Story:** As a club president, I want to see my club's logo next to the page title, so that the booking page feels personalized to my club.

#### Acceptance Criteria

1. WHEN the PresMeet booking page loads, THE Logo_Uploader SHALL render the Club_Logo as an image next to the "Presidents' Meeting Booking" heading
2. WHEN no Club_Logo exists for the user's Club_ID, THE Logo_Uploader SHALL render a placeholder icon indicating no logo is available
3. THE Logo_Uploader SHALL render the Club_Logo at a display size of 48×48 pixels with rounded corners
4. THE Logo_Uploader SHALL display a tooltip on hover indicating the image is clickable for upload

### Requirement 2: Upload Interaction

**User Story:** As a club president, I want to click the logo to upload a new version, so that I can update my club's branding without navigating to a separate page.

#### Acceptance Criteria

1. WHEN the user clicks the Club_Logo or placeholder, THE Logo_Uploader SHALL open a native file selection dialog
2. THE Logo_Uploader SHALL accept only image file types (PNG, JPEG, WebP, GIF)
3. IF the selected file exceeds 5 MB, THEN THE Logo_Uploader SHALL display an error message and reject the file without uploading
4. WHEN a valid file is selected, THE Logo_Uploader SHALL display a loading indicator over the logo area until the upload completes
5. WHEN the upload succeeds, THE Logo_Uploader SHALL display the new logo image immediately without requiring a page refresh

### Requirement 3: Client-Side Image Preparation

**User Story:** As a club president, I want my uploaded image to be processed correctly regardless of the format I provide, so that I don't have to manually resize or convert files.

#### Acceptance Criteria

1. WHEN a file is selected, THE Logo_Uploader SHALL read the file and encode it as a base64 string for transmission to the Upload_Endpoint
2. THE Logo_Uploader SHALL send the base64-encoded image data along with the user's Club_ID and the original file content type to the Upload_Endpoint

### Requirement 4: Backend Upload and Resize

**User Story:** As a system operator, I want uploaded logos to be resized server-side to a consistent dimension, so that all club logos have uniform presentation and storage footprint.

#### Acceptance Criteria

1. WHEN the Upload_Endpoint receives a valid image payload, THE Image_Resizer SHALL resize the image to fit within a 200×200 pixel bounding box while preserving aspect ratio
2. IF the Image_Resizer fails to produce a valid 200×200 pixel result (e.g., corrupt image data, unsupported color mode, processing error), THEN THE Upload_Endpoint SHALL return a 400 error with a descriptive message and SHALL NOT overwrite the existing Club_Logo
3. THE Image_Resizer SHALL convert the resized image to PNG format regardless of the input format
4. WHEN the resized image is ready, THE Upload_Endpoint SHALL write it to the Frontend_Bucket at the path `assets/presmeet/logos/{club_id}.png`, overwriting any existing file at that path
5. THE Upload_Endpoint SHALL set the S3 object content type to `image/png`
6. THE Upload_Endpoint SHALL set the S3 object cache-control header to `max-age=0, must-revalidate` to prevent stale cached versions
7. IF the image payload is not a valid image file, THEN THE Upload_Endpoint SHALL return a 400 error with a descriptive message
8. IF the image payload exceeds 5 MB after base64 decoding, THEN THE Upload_Endpoint SHALL return a 413 error

### Requirement 5: Authentication and Authorization

**User Story:** As a club member, I want to upload a logo for my own club without needing any special role or permission, so that logo management is self-service for every club.

#### Acceptance Criteria

1. THE Upload_Endpoint SHALL require a valid Bearer token in the Authorization header
2. THE Upload_Endpoint SHALL extract the user's Club_ID from the Member record in DynamoDB using the authenticated user's email
3. IF the authenticated user has no Club_ID assigned, THEN THE Upload_Endpoint SHALL return a 403 error
4. THE Upload_Endpoint SHALL NOT require any specific role or permission beyond being an authenticated member with a Club_ID — any such member can upload their own club's logo (self-service)
5. THE Upload_Endpoint SHALL only allow uploading a logo for the club assigned to the authenticated user (the club_id in the request must match the user's assigned club)
6. WHERE the user has a Products_CRUD or Webshop_Management role, THE Upload_Endpoint SHALL allow uploading a logo for any club_id (admin override)

### Requirement 6: Cache Busting

**User Story:** As a club president, I want to see my new logo immediately after uploading, so that I have confidence the upload succeeded.

#### Acceptance Criteria

1. WHEN the upload succeeds, THE Upload_Endpoint SHALL return the logo URL with a cache-busting query parameter appended (timestamp-based)
2. WHEN the Logo_Uploader receives a successful upload response, THE Logo_Uploader SHALL update the displayed image source to the returned URL with the cache-busting parameter
3. THE Logo_Uploader SHALL persist the cache-busting parameter in component state so the fresh image remains visible during the session

### Requirement 7: Error Handling

**User Story:** As a club president, I want clear feedback when something goes wrong with the upload, so that I know what action to take.

#### Acceptance Criteria

1. IF the Upload_Endpoint returns an error, THEN THE Logo_Uploader SHALL display a toast notification with the error message
2. IF a network error occurs during upload, THEN THE Logo_Uploader SHALL display a toast notification indicating the upload failed and suggesting the user try again
3. WHEN an error occurs, THE Logo_Uploader SHALL restore the previous logo image (or placeholder) and remove the loading indicator
