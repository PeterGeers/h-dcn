#!/usr/bin/env python3
"""
Test Google Sheets API Connection
Quick test to verify credentials and sheet access
"""

import os
import sys
import json
from pathlib import Path

def test_credentials_file():
    """Test if credentials file exists and is valid JSON"""
    print("🔍 Testing Google credentials file...")
    
    # Look for credentials file in project root
    project_root = Path(__file__).parent.parent.parent
    creds_path = project_root / '.googleCredentials.json'
    
    print(f"📁 Looking for credentials at: {creds_path}")
    
    if not creds_path.exists():
        print("❌ Credentials file not found!")
        print("💡 Make sure .googleCredentials.json exists in project root")
        return False
    
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)
        
        # Check required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        # Check if it's still the template
        if creds.get('project_id') == 'h-dcn-sheets-api' and 'REPLACE_WITH_ACTUAL' in creds.get('private_key', ''):
            print("⚠️  Credentials file contains template values!")
            print("💡 Please replace with actual service account credentials")
            return False
        
        print("✅ Credentials file looks valid")
        print(f"📧 Service account: {creds.get('client_email')}")
        print(f"🏗️  Project: {creds.get('project_id')}")
        return True
        
    except json.JSONDecodeError:
        print("❌ Credentials file is not valid JSON!")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def test_google_imports():
    """Test if Google API libraries are installed"""
    print("\n🔍 Testing Google API imports...")
    
    try:
        import gspread
        print("✅ gspread imported successfully")
    except ImportError:
        print("❌ gspread not installed!")
        print("💡 Run: pip install gspread")
        return False
    
    try:
        from google.oauth2.service_account import Credentials
        print("✅ google-auth imported successfully")
    except ImportError:
        print("❌ google-auth not installed!")
        print("💡 Run: pip install google-auth")
        return False
    
    return True

def test_google_connection():
    """Test actual connection to Google Sheets API"""
    print("\n🔍 Testing Google Sheets API connection...")
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Load credentials
        project_root = Path(__file__).parent.parent.parent
        creds_path = project_root / '.googleCredentials.json'
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        credentials = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
        gc = gspread.authorize(credentials)
        
        print("✅ Successfully authenticated with Google API")
        
        # Try to list accessible spreadsheets (this will show if service account has access)
        try:
            sheets = gc.openall()
            print(f"📊 Service account has access to {len(sheets)} spreadsheet(s):")
            for sheet in sheets[:5]:  # Show first 5
                print(f"   - {sheet.title}")
            if len(sheets) > 5:
                print(f"   ... and {len(sheets) - 5} more")
                
        except Exception as e:
            print(f"⚠️  Could not list spreadsheets: {e}")
            print("💡 This might be normal if no sheets are shared with service account yet")
        
        return True
        
    except FileNotFoundError:
        print("❌ Credentials file not found!")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Check if:")
        print("   - Google Sheets API is enabled in Google Cloud Console")
        print("   - Service account credentials are correct")
        print("   - Internet connection is working")
        return False

def test_specific_sheet(sheet_name):
    """Test access to specific sheet"""
    print(f"\n🔍 Testing access to sheet: '{sheet_name}'...")
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Load credentials
        project_root = Path(__file__).parent.parent.parent
        creds_path = project_root / '.googleCredentials.json'
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        credentials = Credentials.from_service_account_file(str(creds_path), scopes=scopes)
        gc = gspread.authorize(credentials)
        
        # Try to open specific sheet
        sheet = gc.open(sheet_name)
        print(f"✅ Successfully opened sheet: {sheet.title}")
        
        # Get worksheets
        worksheets = sheet.worksheets()
        print(f"📋 Found {len(worksheets)} worksheet(s):")
        for ws in worksheets:
            print(f"   - {ws.title} ({ws.row_count} rows, {ws.col_count} cols)")
        
        # Try to read first few rows of first worksheet
        if worksheets:
            ws = worksheets[0]
            try:
                headers = ws.row_values(1)
                print(f"📊 Headers in '{ws.title}': {headers[:5]}{'...' if len(headers) > 5 else ''}")
                
                # Count non-empty rows
                all_values = ws.get_all_values()
                non_empty_rows = sum(1 for row in all_values if any(cell.strip() for cell in row))
                print(f"📈 Estimated {non_empty_rows} non-empty rows")
                
            except Exception as e:
                print(f"⚠️  Could not read sheet content: {e}")
        
        return True
        
    except gspread.SpreadsheetNotFound:
        print(f"❌ Sheet '{sheet_name}' not found!")
        print("💡 Check if:")
        print("   - Sheet name is correct (case-sensitive)")
        print("   - Sheet is shared with service account email")
        return False
    except Exception as e:
        print(f"❌ Failed to access sheet: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Google Sheets API Connection Test")
    print("=" * 50)
    
    # Test 1: Credentials file
    if not test_credentials_file():
        print("\n❌ Credentials test failed. Please fix before continuing.")
        return False
    
    # Test 2: Python imports
    if not test_google_imports():
        print("\n❌ Import test failed. Please install required packages.")
        print("💡 Run: pip install -r backend/requirements.txt")
        return False
    
    # Test 3: Google API connection
    if not test_google_connection():
        print("\n❌ Google API connection failed.")
        return False
    
    # Test 4: Specific sheet (if provided)
    if len(sys.argv) > 1:
        sheet_name = sys.argv[1]
        if not test_specific_sheet(sheet_name):
            print(f"\n❌ Failed to access sheet '{sheet_name}'")
            return False
    else:
        print("\n💡 To test specific sheet access, run:")
        print("   python test_google_connection.py 'HDCN Ledenbestand 2026'")
    
    print("\n🎉 All tests passed!")
    print("✅ Google Sheets API is ready for migration")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)