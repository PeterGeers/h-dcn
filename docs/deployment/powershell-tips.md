# PowerShell Deployment Tips

## Bypass "More" Prompts

All deployment scripts now include this line to prevent AWS CLI from pausing with "more" prompts:

```powershell
# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""
```

## What This Fixes

### Before

- AWS CLI commands would pause with `--More--` prompts
- Required manual pressing of space/enter to continue
- Interrupted automated deployments
- Made scripts non-interactive

### After

- Commands run continuously without pausing
- Fully automated deployment process
- No manual intervention required
- Scripts can run unattended

## Scripts Updated

All deployment and utility scripts now include the bypass:

- `scripts/deployment/deploy-frontend-safe.ps1`
- `scripts/deployment/deploy-production-frontend.ps1`
- `scripts/deployment/deploy-production-frontend-quiet.ps1`
- `scripts/deployment/build-and-deploy-fast.ps1`
- `scripts/deployment/deploy-with-progress.ps1`
- `scripts/utilities/fix-product-image-urls.ps1`

## Manual Usage

If running AWS CLI commands manually and want to avoid prompts:

```powershell
# Set for current session
$env:AWS_PAGER = ""

# Or run individual commands with --no-paginate
aws s3 ls --no-paginate
aws cloudfront list-distributions --no-paginate
```

## Alternative Methods

### Option 1: Environment Variable (Recommended)

```powershell
$env:AWS_PAGER = ""
```

### Option 2: AWS CLI Flag

```powershell
aws s3 sync build/ s3://bucket --no-paginate
```

### Option 3: Global AWS Config

Add to `~/.aws/config`:

```ini
[default]
cli_pager=
```

## Best Practices

1. **Always set in scripts**: Include `$env:AWS_PAGER = ""` at the top of deployment scripts
2. **Test locally first**: Run scripts locally before automation
3. **Use in CI/CD**: Essential for automated deployment pipelines
4. **Document usage**: Include in script comments for future reference

## Troubleshooting

### If Prompts Still Appear

1. Check if `$env:AWS_PAGER` is set correctly
2. Verify AWS CLI version (newer versions respect this better)
3. Use `--no-paginate` flag as fallback
4. Check for other pager settings in AWS config

### For Long Outputs

- The bypass works for all AWS CLI commands
- No size limit on output
- Particularly useful for `s3 sync`, `cloudfront list-distributions`, etc.
- Prevents timeouts in automated environments
