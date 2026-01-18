# Google Sheets API Setup Instructions

## Prerequisites

1. **Google Cloud Console Access**: You need access to Google Cloud Console
2. **Google Sheet Access**: The Google Sheet must be accessible to you

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
   - **Recommended name**: `h-dcn-sheets-api`
3. Note the Project ID for later use

## Step 2: Enable Google Sheets API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click on it and press **Enable**
4. Also enable "Google Drive API" (required for sheet access)

## Step 3: Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in details:
   - **Service account name**: `h-dcn-migration`
   - **Service account ID**: `h-dcn-migration` (auto-generated)
   - **Description**: `Service account for H-DCN member data migration`
4. Click **Create and Continue**
5. Skip role assignment (click **Continue**)
6. Skip user access (click **Done**)

## Step 4: Generate Service Account Key

1. In the **Credentials** page, find your service account
2. Click on the service account email
3. Go to **Keys** tab
4. Click **Add Key** > **Create New Key**
5. Select **JSON** format
6. Click **Create**
7. The JSON file will download automatically

## Step 5: Update Credentials File

1. Open the downloaded JSON file
2. Copy its contents
3. Replace the content in `.googleCredentials.json` with the actual credentials
4. The file should look like:

```json
{
  "type": "service_account",
  "project_id": "your-actual-project-id",
  "private_key_id": "actual-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nactual-private-key\n-----END PRIVATE KEY-----\n",
  "client_email": "h-dcn-migration@your-project.iam.gserviceaccount.com",
  "client_id": "actual-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/h-dcn-migration%40your-project.iam.gserviceaccount.com"
}
```

## Step 6: Share Google Sheet with Service Account

1. Open your Google Sheet ("HDCN Ledenbestand 2026")
2. Click **Share** button (top right)
3. Add the service account email as a viewer:
   - Email: `h-dcn-migration@your-project.iam.gserviceaccount.com`
   - Role: **Viewer**
4. Click **Send**

## Step 7: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 8: Test the Connection

```bash
cd backend/scripts
python import_members_sheets.py "HDCN Ledenbestand 2026" "Ledenbestand"
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Keep credentials secure**: Never commit `.googleCredentials.json` to version control
2. **Add to .gitignore**: Ensure the credentials file is ignored
3. **Limit permissions**: Service account only has read access to sheets
4. **Rotate keys**: Periodically rotate service account keys
5. **Monitor usage**: Check Google Cloud Console for API usage

## Troubleshooting

### Common Issues

1. **"Credentials not found"**

   - Check file path: `.googleCredentials.json` should be in project root
   - Verify file permissions

2. **"Sheet not found"**

   - Verify sheet name exactly matches (case-sensitive)
   - Ensure service account has access to the sheet

3. **"Permission denied"**

   - Check if APIs are enabled (Sheets + Drive)
   - Verify service account has viewer access to sheet

4. **"Invalid credentials"**
   - Re-download service account key
   - Check JSON format is valid

### Testing Connection

```python
# Test script to verify connection
import gspread
from google.oauth2.service_account import Credentials

def test_connection():
    try:
        creds = Credentials.from_service_account_file('.googleCredentials.json')
        gc = gspread.authorize(creds)
        sheet = gc.open("HDCN Ledenbestand 2026")
        print(f"✅ Successfully connected to: {sheet.title}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
```

## Migration Benefits

✅ **Eliminates CSV export issues**
✅ **Real-time data access**
✅ **Better data type handling**
✅ **Automatic column shift detection**
✅ **Enhanced data quality logging**
✅ **No manual download steps**
