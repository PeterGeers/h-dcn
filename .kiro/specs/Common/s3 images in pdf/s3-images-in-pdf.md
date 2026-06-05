# S3 Images in PDF Generation

## Overview

WeasyPrint cannot authenticate against S3 presigned URLs or private buckets during HTML-to-PDF rendering. The solution is to **download the image server-side, base64-encode it, and embed it as a data URI** in the HTML before passing it to WeasyPrint.

## The Pattern: Download → Base64 Encode → Embed Inline

```
S3 Bucket  →  boto3 get_object  →  base64 encode  →  data URI  →  <img src="data:...">  →  WeasyPrint PDF
```

### Step-by-step

1. **Fetch the image bytes** from S3 using `boto3.get_object`
2. **Base64-encode** the binary content
3. **Build a data URI** (`data:{content_type};base64,{encoded}`)
4. **Inject into the HTML template** as an `<img src="...">` tag
5. **Render with WeasyPrint** — the image is self-contained, no external fetches needed

## Implementation

### Core Logic (`services/logo_resolver.py`)

```python
import base64
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')
obj = s3_client.get_object(Bucket=bucket, Key=s3_key)
content_type = obj['ContentType']
b64 = base64.b64encode(obj['Body'].read()).decode('utf-8')
data_uri = f'data:{content_type};base64,{b64}'
```

### Usage in PDF Generator (`services/pdf_generator_service.py`)

```python
logo_url = self._get_tenant_logo(tenant)  # returns data URI or None
logo_tag = f'<img src="{logo_url}" class="logo" />' if logo_url else ''

# Insert into HTML template
html = template.replace('{{logo}}', logo_tag)

# Render to PDF
pdf_bytes = weasyprint.HTML(string=html).write_pdf()
```

### HTML Template

```html
<div class="header">
  <div>{{logo}}</div>
  <div><h2>{{invoice_number}}</h2></div>
</div>
```

## Why Data URIs (Not Presigned URLs)

| Approach                     | Problem                                                           |
| ---------------------------- | ----------------------------------------------------------------- |
| Presigned URL in `<img src>` | WeasyPrint may fail to fetch (timeouts, redirects, CORS)          |
| Public S3 URL                | Security risk — exposes bucket contents                           |
| **Base64 data URI**          | ✅ Self-contained, no network calls during render, no auth needed |

## Adding More S3 Images to PDFs

Follow this pattern for any new image (e.g., signatures, stamps, product photos):

```python
def fetch_s3_image_as_data_uri(bucket: str, key: str) -> Optional[str]:
    """Fetch an S3 object and return as base64 data URI."""
    try:
        s3_client = boto3.client('s3')
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        content_type = obj['ContentType']
        b64 = base64.b64encode(obj['Body'].read()).decode('utf-8')
        return f'data:{content_type};base64,{b64}'
    except ClientError as e:
        logger.warning("Failed to fetch S3 image (key=%s): %s", key, e)
        return None
```

Then in your HTML template:

```python
img_uri = fetch_s3_image_as_data_uri(bucket, key)
img_tag = f'<img src="{img_uri}" />' if img_uri else ''
html = template.replace('{{placeholder}}', img_tag)
```

## Storage Provider Abstraction

The `logo_resolver.py` module handles both storage providers transparently:

- **Google Drive (legacy)**: HTTP GET to `lh3.googleusercontent.com` → base64 encode
- **S3 (shared/tenant)**: `boto3.get_object` → base64 encode

The provider is determined by the tenant's `storage.invoice_provider` parameter (`google_drive`, `s3_shared`, or `s3_tenant`).

## Performance Considerations

- Base64 encoding adds ~33% size overhead to the binary image
- Keep images reasonably sized (logos typically < 100KB)
- Images are fetched once per PDF generation — no caching between requests
- For PDFs with many images, consider fetching in parallel or implementing a short-lived cache

## Related Files

- `backend/src/services/logo_resolver.py` — Provider-aware image fetching
- `backend/src/services/pdf_generator_service.py` — HTML template rendering + WeasyPrint
- `backend/src/templates/zzp_invoice_default.html` — Invoice HTML template
- `.kiro/specs/Solved/20260526 s3-shared-bucket-infrastructure/` — S3 architecture spec
