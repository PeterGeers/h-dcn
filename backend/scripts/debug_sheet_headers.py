#!/usr/bin/env python3
"""
Debug script to check Google Sheets headers for duplicates
"""

import gspread
from google.oauth2.service_account import Credentials
import os
from collections import Counter

def load_google_credentials():
    """Load Google service account credentials"""
    creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.googleCredentials.json')
    
    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Google credentials not found at {creds_path}")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return credentials

def debug_sheet_headers(sheet_name: str, worksheet_name: str = 'Ledenbestand'):
    """Debug Google Sheets headers"""
    try:
        credentials = load_google_credentials()
        gc = gspread.authorize(credentials)
        
        sheet = gc.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        
        # Get the header row
        headers = worksheet.row_values(1)
        
        print(f"📊 Sheet: {sheet_name} -> {worksheet_name}")
        print(f"📋 Total columns: {len(headers)}")
        print(f"\n📝 All headers:")
        
        for i, header in enumerate(headers):
            print(f"  {i+1:2d}. '{header}'")
        
        # Check for duplicates
        header_counts = Counter(headers)
        duplicates = {header: count for header, count in header_counts.items() if count > 1}
        
        if duplicates:
            print(f"\n❌ Duplicate headers found:")
            for header, count in duplicates.items():
                print(f"  '{header}' appears {count} times")
                
                # Show positions of duplicates
                positions = [i+1 for i, h in enumerate(headers) if h == header]
                print(f"    Positions: {positions}")
        else:
            print(f"\n✅ No duplicate headers found")
        
        # Check for empty headers
        empty_headers = [i+1 for i, header in enumerate(headers) if not header.strip()]
        if empty_headers:
            print(f"\n⚠️  Empty headers at positions: {empty_headers}")
        
        return headers
        
    except Exception as e:
        print(f"❌ Failed to debug sheet: {str(e)}")
        return None

if __name__ == "__main__":
    debug_sheet_headers("HDCN Ledenbestand 2026", "Ledenbestand")