#!/usr/bin/env python3
import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

try:
    from handler.get_events.app import lambda_handler
    print("✅ get_events handler imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    print(f"Error type: {type(e)}")
    
try:
    from handler.create_member.app import lambda_handler as create_handler
    print("✅ create_member handler imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    print(f"Error type: {type(e)}")