# Custom Domain Setup for testportal.h-dcn.nl

## Current Status

- **Working Solution**: Domain forwarding via Squarespace
- **URL Behavior**: testportal.h-dcn.nl → https://de1irtdutlxqu.cloudfront.net/
- **Status**: Fully functional, all features working

## Future Enhancement: Custom Domain (URL Masking)

### Goal

Make users see `https://testportal.h-dcn.nl` in the URL bar instead of the CloudFront URL.

### Required Steps

#### 1. Request New SSL Certificate

```powershell
aws acm request-certificate \
  --domain-name testportal.h-dcn.nl \
  --validation-method DNS \
  --region us-east-1
```

#### 2. Add DNS Validation Record

- Get validation record from ACM certificate
- Add CNAME record in Squarespace DNS settings
- Wait for validation (up to 48 hours)

#### 3. Update CloudFront Distribution

```powershell
# Add custom domain alias to CloudFront distribution E2QTMDOE6H0R87
# Update SSL certificate to use validated ACM certificate
# This requires the distribution config update
```

#### 4. Change DNS Configuration

**Remove**: Domain forwarding rule in Squarespace
**Add**: CNAME record pointing to CloudFront:

```
Name: testportal
Type: CNAME
Value: de1irtdutlxqu.cloudfront.net
```

### Benefits of Custom Domain

- ✅ Professional URL appearance
- ✅ Better branding consistency
- ✅ No redirect behavior
- ✅ Improved user trust

### Risks/Considerations

- ⚠️ Temporary downtime during DNS changes
- ⚠️ SSL certificate validation can fail
- ⚠️ DNS propagation delays (up to 48 hours)
- ⚠️ More complex troubleshooting

### Current Working Solution

The domain forwarding approach is:

- ✅ Reliable and stable
- ✅ No maintenance required
- ✅ All functionality preserved
- ✅ Good enough for production use

### When to Implement

Consider implementing custom domain when:

- You have dedicated time for potential troubleshooting
- You can handle temporary downtime if issues occur
- The URL appearance becomes a business priority
- You want to implement additional CloudFront features

---

**Last Updated**: December 30, 2025  
**Current Solution**: Domain Forwarding (Working)  
**Future Enhancement**: Custom Domain Setup (Optional)
