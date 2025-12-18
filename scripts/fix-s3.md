# S3 Fix Scripts Documentation

## 🎯 Overview

The H-DCN project uses multiple PowerShell scripts to resolve common S3 deployment issues with React Single Page Applications (SPA). These scripts address specific problems that occur when hosting React Router applications on S3.

## 🔧 Available Fix Scripts

### Content-Type Issues

#### `fix-content-type.ps1`
**Purpose**: Sets correct MIME type for index.html
**Problem**: S3 may serve HTML files with incorrect content-type headers
**Solution**: 
- Sets `text/html` content-type for index.html
- Adds cache-control headers to prevent caching issues

```powershell
.\fix-content-type.ps1
```

#### `fix-s3-content-types.ps1`
**Purpose**: Comprehensive content-type fixing for all static assets
**Problem**: CSS and JS files served with wrong MIME types
**Solution**:
- Sets `text/css` for CSS files
- Sets `application/javascript` for JS files
- Configures S3 website hosting
- Sets proper cache headers

```powershell
.\fix-s3-content-types.ps1
```

### React Router Issues

#### `fix-s3-routing.ps1`
**Purpose**: Complete S3 routing configuration with testing
**Problem**: React Router routes return 404 on direct access
**Solution**:
- Configures ErrorDocument to serve index.html
- Sets no-cache headers on index.html
- Tests multiple routing endpoints
- Provides comprehensive verification

```powershell
.\fix-s3-routing.ps1
```

#### `fix-s3-simple.ps1`
**Purpose**: Simple ErrorDocument approach without routing rules
**Problem**: Complex routing rules causing issues
**Solution**:
- Uses basic ErrorDocument configuration
- Removes problematic routing rules
- Cleans up incorrectly placed HTML files
- Triggers fresh deployment

```powershell
.\fix-s3-simple.ps1
```

#### `fix-s3-advanced-routing.ps1`
**Purpose**: Advanced routing rules for sophisticated SPA handling
**Problem**: Need granular control over 404 redirects
**Solution**:
- Implements S3 RoutingRules
- Handles 404 errors with proper redirects
- Maintains original URL structure
- Provides configuration verification

```powershell
.\fix-s3-advanced-routing.ps1
```

#### `fix-s3-specific-routing.ps1`
**Purpose**: Prevents static assets from being redirected
**Problem**: JS/CSS files incorrectly redirected to index.html
**Solution**:
- Specific routing rules for HTML routes only
- Prevents asset file redirection
- Checks for missing chunk files
- Uses HTTP 200 redirects

```powershell
.\fix-s3-specific-routing.ps1
```

### Deployment Issues

#### `fix-s3-deployment.ps1`
**Purpose**: Complete clean rebuild and redeploy process
**Problem**: Corrupted or incomplete S3 deployment
**Solution**:
- Cleans build and node_modules
- Fresh npm install and build
- Clears entire S3 bucket
- Uploads with proper configuration
- Configures React Router support

```powershell
.\fix-s3-deployment.ps1
```

## 🚨 Common Problems & Solutions

### Problem: React Routes Return 404

**Symptoms**:
- Direct access to `/members` or `/products` shows 404
- Refresh on any route except `/` fails
- Deep linking doesn't work

**Solutions** (in order of preference):
1. `fix-s3-simple.ps1` - Start with simple approach
2. `fix-s3-routing.ps1` - Comprehensive solution with testing
3. `fix-s3-advanced-routing.ps1` - If complex routing needed

### Problem: Static Assets Not Loading

**Symptoms**:
- CSS styles not applied
- JavaScript files return HTML content
- Console shows MIME type errors

**Solutions**:
1. `fix-s3-content-types.ps1` - Fix all content types
2. `fix-s3-specific-routing.ps1` - Prevent asset redirection

### Problem: Caching Issues

**Symptoms**:
- Old version of app loads after deployment
- Changes not visible immediately
- Browser shows cached content

**Solutions**:
1. `fix-content-type.ps1` - Add no-cache headers
2. `fix-s3-deployment.ps1` - Complete clean deployment

### Problem: Deployment Corruption

**Symptoms**:
- Missing files in S3 bucket
- Partial deployment
- Build artifacts in wrong locations

**Solutions**:
1. `fix-s3-deployment.ps1` - Complete clean rebuild

## 🔄 Usage Workflow

### Quick Fix (Most Common)
```powershell
# For routing issues
.\fix-s3-simple.ps1

# For content-type issues
.\fix-s3-content-types.ps1
```

### Comprehensive Fix
```powershell
# Complete deployment fix
.\fix-s3-deployment.ps1

# Then apply routing
.\fix-s3-routing.ps1
```

### Debugging Approach
```powershell
# 1. Start simple
.\fix-s3-simple.ps1

# 2. If issues persist, try comprehensive
.\fix-s3-routing.ps1

# 3. For complex cases
.\fix-s3-advanced-routing.ps1

# 4. Last resort - clean slate
.\fix-s3-deployment.ps1
```

## 🧪 Testing After Fixes

### Manual Testing
```bash
# Test main routes
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/members
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/products

# Test static assets
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/static/css/main.css
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/static/js/main.js
```

### Browser Testing
1. Open website in incognito mode
2. Navigate to different routes
3. Refresh on each route
4. Check browser console for errors
5. Verify CSS/JS loading correctly

## 📋 Verification Commands

### Check S3 Configuration
```powershell
# View website configuration
aws s3api get-bucket-website --bucket hdcn-dashboard-frontend

# List bucket contents
aws s3 ls s3://hdcn-dashboard-frontend/ --recursive

# Check specific file content-type
aws s3api head-object --bucket hdcn-dashboard-frontend --key index.html
```

### Check File Integrity
```powershell
# Compare local build with S3
aws s3 sync build/ s3://hdcn-dashboard-frontend --dryrun

# Check for missing files
aws s3 ls s3://hdcn-dashboard-frontend/static/js/ | findstr "chunk.js"
```

## 🎯 Best Practices

### When to Use Each Script

1. **Daily Development**: Use `fix-s3-simple.ps1` for quick routing fixes
2. **Production Issues**: Use `fix-s3-routing.ps1` for comprehensive solution
3. **Asset Problems**: Use `fix-s3-content-types.ps1` for MIME type issues
4. **Major Issues**: Use `fix-s3-deployment.ps1` for complete reset

### Prevention Tips

1. **Always test routes** after deployment
2. **Check browser console** for errors
3. **Use incognito mode** to avoid cache issues
4. **Verify S3 configuration** after changes
5. **Monitor CloudWatch logs** for 404 errors

## 🚨 Emergency Procedures

### Production Down
```powershell
# 1. Quick routing fix
.\fix-s3-simple.ps1

# 2. If still broken, full reset
.\fix-s3-deployment.ps1

# 3. Verify immediately
curl -I http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/
```

### Asset Loading Issues
```powershell
# 1. Fix content types
.\fix-s3-content-types.ps1

# 2. If routing interferes with assets
.\fix-s3-specific-routing.ps1
```

## 📚 Technical Background

### React Router + S3 Challenge
React Router uses client-side routing, but S3 only serves static files. When a user visits `/members` directly, S3 looks for a file at that path, which doesn't exist, resulting in a 404.

### S3 Website Configuration Solutions
1. **ErrorDocument**: Redirect all 404s to index.html
2. **RoutingRules**: Conditional redirects based on error codes
3. **Content-Type**: Ensure proper MIME types for all assets

### Cache Control Strategy
- **index.html**: No cache (always fresh)
- **Static assets**: Long cache (versioned filenames)
- **API responses**: No cache (dynamic content)

---

**Maintenance**: Review and update these scripts quarterly
**Owner**: H-DCN Development Team
**Last Updated**: October 2025