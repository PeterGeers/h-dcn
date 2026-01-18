# Parquet System Removal - Deployment Guide

## Summary of Changes

All Parquet-related code and resources have been removed from the codebase:

### Backend Changes

1. ✅ Deleted Lambda function directories:
   - `backend/handler/generate_member_parquet/`
   - `backend/handler/download_parquet/`

2. ✅ Updated SAM template (`backend/template.yaml`):
   - Removed `GenerateMemberParquetFunction` resource
   - Removed `DownloadParquetFunction` resource
   - Removed Parquet API Gateway endpoints:
     - `POST /analytics/generate-parquet`
     - `GET /analytics/download-parquet/{filename}`
   - Removed `GenerateMemberParquetFunctionName` output

3. ✅ Cleaned up S3 storage:
   - Deleted all files in `s3://my-hdcn-bucket/analytics/parquet/members/`

### Frontend Changes

1. ✅ Deleted Parquet service files:
   - `frontend/src/services/ParquetDataService.ts`
   - `frontend/src/modules/members/services/parquetDataService.ts`

2. ✅ Deleted Parquet hooks:
   - `frontend/src/hooks/useParquetData.ts`
   - `frontend/src/modules/members/hooks/useParquetData.ts`
   - `frontend/src/modules/members/hooks/useMemberParquetData.ts`

3. ✅ Deleted Parquet types:
   - `frontend/src/types/ParquetTypes.ts`

4. ✅ Deleted Parquet test files:
   - `frontend/src/services/__tests__/ParquetDataService.integration.test.ts`
   - `frontend/src/services/__tests__/ParquetDataService.test.ts`
   - `frontend/src/services/__tests__/ParquetDataService.regionalFiltering.test.ts`

5. ✅ Updated WebWorkerManager:
   - Removed Parquet-specific type imports
   - Replaced with generic worker types

## Deployment Steps

### 1. Backend Deployment

Deploy the updated SAM template to remove Parquet Lambda functions:

```powershell
cd backend
sam build
sam deploy --config-env production
```

**Expected outcome:**

- `GenerateMemberParquetFunction` will be deleted from CloudFormation stack
- `DownloadParquetFunction` will be deleted from CloudFormation stack
- API Gateway endpoints `/analytics/generate-parquet` and `/analytics/download-parquet/{filename}` will be removed

### 2. Frontend Deployment

Build and deploy the updated frontend:

```powershell
cd frontend
npm run build
# Deploy to CloudFront/S3 using your deployment script
```

**Expected outcome:**

- No Parquet-related code in production bundle
- Smaller bundle size (removed unused code)

### 3. Verification Steps

After deployment, verify:

1. **Backend verification:**

   ```powershell
   # Check that Parquet functions are gone
   aws lambda list-functions --query "Functions[?contains(FunctionName, 'Parquet')]"
   # Should return empty array

   # Check API Gateway endpoints
   aws apigateway get-resources --rest-api-id <your-api-id>
   # Should not show /analytics/generate-parquet or /analytics/download-parquet
   ```

2. **Frontend verification:**
   - Open browser console
   - Navigate to member reporting page
   - Check for any errors related to Parquet
   - Verify member data loads correctly using new regional filtering API

3. **CloudWatch Logs:**
   - Monitor logs for any errors
   - Verify no references to Parquet functions

## Rollback Plan

If issues occur, you can rollback:

1. **Backend rollback:**

   ```powershell
   cd backend
   git checkout HEAD~1 -- handler/generate_member_parquet handler/download_parquet template.yaml
   sam build
   sam deploy --config-env production
   ```

2. **Frontend rollback:**
   ```powershell
   cd frontend
   git checkout HEAD~1 -- src/services/ParquetDataService.ts src/hooks/useParquetData.ts
   npm run build
   # Redeploy
   ```

## Notes

- The new regional filtering system (`GET /api/members`) is already deployed and working
- This deployment only removes the old Parquet system
- No functionality is lost - member reporting continues to work with the new system
- S3 storage has already been cleaned up (no rollback needed for S3)

## Post-Deployment Checklist

- [ ] Backend deployment successful
- [ ] Frontend deployment successful
- [ ] No errors in CloudWatch logs
- [ ] Member reporting page loads correctly
- [ ] Regional filtering works as expected
- [ ] No console errors in browser
- [ ] Parquet Lambda functions deleted from AWS
- [ ] Parquet API endpoints removed from API Gateway
