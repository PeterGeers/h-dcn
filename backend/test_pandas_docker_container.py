#!/usr/bin/env python3
"""
Test script to verify pandas and pyarrow availability in Docker container
This script simulates the parquet generation function to ensure all dependencies work correctly.
"""

import sys
import json
from datetime import datetime

def test_imports():
    """Test if all required libraries can be imported"""
    print("🔍 Testing library imports...")
    
    try:
        import pandas as pd
        print(f"✅ pandas {pd.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pandas: {e}")
        return False
    
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        print(f"✅ pyarrow {pa.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pyarrow: {e}")
        return False
    
    try:
        import boto3
        print(f"✅ boto3 {boto3.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import boto3: {e}")
        return False
    
    return True

def test_parquet_generation():
    """Test basic parquet file generation functionality"""
    print("\n🔍 Testing parquet generation...")
    
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        import io
        
        # Create sample member data
        sample_data = [
            {
                'lidnummer': '12345',
                'voornaam': 'Test',
                'achternaam': 'Member',
                'geboortedatum': '1980-01-01',
                'tijdstempel': '2020-01-01',
                'status': 'Actief',
                'regio': 'Noord',
                'lidmaatschap': 'Gewoon',
                'email': 'test@example.com',
                'generated_at': datetime.utcnow()
            }
        ]
        
        # Convert to DataFrame
        df = pd.DataFrame(sample_data)
        df['generated_at'] = pd.to_datetime(df['generated_at']).astype('datetime64[ms]')
        
        # Define schema
        schema = pa.schema([
            ('lidnummer', pa.string()),
            ('voornaam', pa.string()),
            ('achternaam', pa.string()),
            ('geboortedatum', pa.string()),
            ('tijdstempel', pa.string()),
            ('status', pa.string()),
            ('regio', pa.string()),
            ('lidmaatschap', pa.string()),
            ('email', pa.string()),
            ('generated_at', pa.timestamp('ms')),
        ])
        
        # Convert to PyArrow Table
        table = pa.Table.from_pandas(df, schema=schema)
        
        # Write to memory buffer
        buffer = io.BytesIO()
        pq.write_table(table, buffer, compression='snappy')
        buffer.seek(0)
        
        # Read back to verify
        buffer.seek(0)
        read_table = pq.read_table(buffer)
        read_df = read_table.to_pandas()
        
        print(f"✅ Successfully generated and read parquet data")
        print(f"   - Records: {len(read_df)}")
        print(f"   - Columns: {list(read_df.columns)}")
        print(f"   - Buffer size: {len(buffer.getvalue())} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Parquet generation test failed: {e}")
        return False

def test_auth_layer():
    """Test if auth layer utilities are available"""
    print("\n🔍 Testing auth layer imports...")
    
    try:
        from shared.auth_utils import (
            extract_user_credentials, 
            validate_permissions, 
            create_success_response, 
            create_error_response
        )
        print("✅ Auth layer utilities imported successfully")
        return True
    except ImportError as e:
        print(f"⚠️ Auth layer not available (expected in container): {e}")
        print("   This is normal when running outside the container")
        return True  # Not a failure for local testing

def main():
    """Run all tests"""
    print("🐳 Docker Container Pandas/PyArrow Verification")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test parquet generation
    if not test_parquet_generation():
        all_passed = False
    
    # Test auth layer (optional)
    test_auth_layer()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Container dependencies are working correctly.")
        print("✅ Ready to deploy Docker container to AWS Lambda")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the container configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()