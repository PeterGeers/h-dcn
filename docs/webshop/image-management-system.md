# Webshop Image Management System

## Overview

This document describes the improved image management system for the H-DCN webshop after the restoration and fixes implemented on December 30, 2025.

## Image Naming Convention

### Current System (After Fix)

- **Logical naming**: Images use product ID as filename (e.g., `G2.jpg`, `TH-60.jpg`)
- **Consistent structure**: `product-images/{PRODUCT_ID}.{extension}`
- **Easy maintenance**: Clear relationship between product and image file

### Previous System (Before Fix)

- **Timestamped naming**: Images used timestamps (e.g., `1758647210252-G2.jpg`)
- **Difficult maintenance**: No clear relationship between filename and product
- **Cleanup issues**: Hard to identify unused images

## Image Upload Logic

### For Existing Products

When uploading images for products with existing IDs:

```typescript
// New image will be named: product-images/G2.jpg
uploadToS3(file, "G2");
```

### For New Products

When creating new products without IDs:

```typescript
// Temporary timestamped name until product gets an ID
uploadToS3(file); // Creates: product-images/1767104567890-newimage.jpg
```

## Database Image URLs

All products now store logical image URLs:

```json
{
  "id": "G2",
  "image": [
    "https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/product-images/G2.jpg"
  ],
  "images": [
    "https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/product-images/G2.jpg"
  ]
}
```

## Restored Images

### Successfully Restored (23 images)

- BS-U.jpg, DA-D.jpg, DA-H.jpg, DB-D.jpg, DB-H.jpg
- G1.jpg, G2.jpg, G3.jpg, G4.jpg, G8.jpg, G9.jpg, G10.jpg, G12.jpg, G13.jpg, G15.jpg
- RC-H.jpg, SD.jpg, SH.jpg
- TD.jpg, TD-60.jpg, TH.jpg, TH-60.jpg, TH-65.jpg

### Database Updates

All 23 products were updated to use the new logical image URLs via automated script.

## Image Management Features

### Upload Process

1. **File Selection**: User selects image files in product management
2. **Logical Naming**: System uses product ID for filename
3. **S3 Upload**: Image uploaded to `product-images/` folder
4. **Database Update**: Product record updated with new image URL
5. **Immediate Display**: Image appears in webshop immediately

### Cleanup System

- **Unused Image Detection**: System can identify orphaned images
- **Bulk Cleanup**: Remove images not referenced by any product
- **Safe Operations**: Only removes truly unused files

## File Structure

```
S3 Bucket: my-hdcn-bucket
├── product-images/
│   ├── G1.jpg          # Badge - H-DCN lidmaatschap
│   ├── G2.jpg          # Badge - Nr.1 H-DC Nederland
│   ├── G3.jpg          # Badge - H-DCN logo klein
│   ├── ...
│   ├── TH-60.jpg       # T-shirt heren 60 jaar
│   └── TH-65.jpg       # T-shirt heren Diamant
├── imagesWebsite/
│   ├── hdcnFavico.png  # H-DCN logo (200x200px)
│   └── info-icon-orange.svg # Info button icon
└── static/             # Frontend application files
```

## Deployment Safety

### Safe Deployment Script

Created `deploy-frontend-safe.ps1` that:

- Only syncs frontend files (`static/`, `index.html`, etc.)
- Preserves user-uploaded content (`product-images/`, `imagesWebsite/`)
- Prevents accidental deletion of user data

### Never Use Again

- `aws s3 sync --delete` on buckets with user content
- Bulk operations without excluding user directories

## Backup Strategy

### ProductA.json Reference

The `ProductA.json` file serves as a backup reference containing:

- Product names and descriptions
- Correct image associations
- Pricing and category information
- Size/option data

### Regular Backups Recommended

- Export product data regularly
- Backup S3 bucket contents
- Version control for configuration files

## Troubleshooting

### Images Not Displaying

1. Check image URL in database matches S3 filename
2. Verify image exists in S3 `product-images/` folder
3. Check CloudFront cache (may need invalidation)
4. Confirm image permissions (should be publicly readable)

### Upload Issues

1. Verify AWS credentials are configured
2. Check S3 bucket permissions
3. Ensure product ID is valid for logical naming
4. Check file size limits and formats

## Future Improvements

### Recommended Enhancements

1. **Image Optimization**: Automatic resizing and compression
2. **Multiple Formats**: WebP support for better performance
3. **CDN Optimization**: Better caching strategies
4. **Backup Automation**: Scheduled backups of product data
5. **Image Validation**: Check image quality and dimensions

### Migration Path

For any remaining timestamped images:

1. Identify products with old URLs
2. Update to logical naming convention
3. Clean up old timestamped files
4. Verify all images display correctly

## Contact

For issues with the image management system, refer to this documentation or check the implementation in:

- `frontend/src/modules/products/services/s3Upload.tsx`
- `scripts/utilities/fix-product-image-urls.ps1`
- `scripts/deployment/deploy-frontend-safe.ps1`
