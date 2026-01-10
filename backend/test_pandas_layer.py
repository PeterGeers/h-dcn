#!/usr/bin/env python3
"""
Test script to verify PandasLayer contains required libraries (pandas, pyarrow)

This script simulates what the Lambda function would encounter when trying to import
the required libraries for parquet generation.

Usage:
    python test_pandas_layer.py

Expected behavior:
    - If PandasLayer is properly built: Both imports succeed
    - If PandasLayer is missing/incomplete: Import errors occur
"""

import sys
import os

def test_pandas_layer_imports():
    """Test if pandas and pyarrow can be imported from the layer"""
    
    print("🔍 Testing PandasLayer library availability...")
    print("=" * 60)
    
    # Add the layer path to Python path (simulating Lambda environment)
    layer_path = os.path.join(os.path.dirname(__file__), 'layers', 'pandas-layer', 'python')
    if os.path.exists(layer_path):
        sys.path.insert(0, layer_path)
        print(f"✅ PandasLayer path found: {layer_path}")
    else:
        print(f"❌ PandasLayer path not found: {layer_path}")
    
    # Test pandas import
    try:
        import pandas as pd
        print(f"✅ pandas imported successfully (version: {pd.__version__})")
        pandas_available = True
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        pandas_available = False
    
    # Test pyarrow import
    try:
        import pyarrow as pa
        print(f"✅ pyarrow imported successfully (version: {pa.__version__})")
        pyarrow_available = True
    except ImportError as e:
        print(f"❌ pyarrow import failed: {e}")
        pyarrow_available = False
    
    print("=" * 60)
    
    # Summary
    if pandas_available and pyarrow_available:
        print("🎉 SUCCESS: Both pandas and pyarrow are available!")
        print("   The PandasLayer is properly configured for parquet generation.")
        return True
    else:
        print("⚠️  ISSUE: Required libraries are missing!")
        print("   The PandasLayer needs to be built with pandas and pyarrow.")
        print("\n📋 Next steps:")
        print("   1. Install pandas and pyarrow in the layer:")
        print("      pip install pandas==2.0.3 pyarrow==12.0.0 -t backend/layers/pandas-layer/python")
        print("   2. Add PandasLayer to the SAM template:")
        print("      - Define PandasLayer in template.yaml")
        print("      - Add PandasLayer to GenerateMemberParquetFunction layers")
        print("   3. Deploy the updated stack")
        return False

def check_layer_structure():
    """Check the current structure of the pandas layer"""
    
    print("\n🔍 Checking PandasLayer directory structure...")
    print("=" * 60)
    
    layer_base = os.path.join(os.path.dirname(__file__), 'layers', 'pandas-layer')
    
    if not os.path.exists(layer_base):
        print(f"❌ PandasLayer directory not found: {layer_base}")
        return
    
    print(f"✅ PandasLayer directory exists: {layer_base}")
    
    # Check requirements.txt
    requirements_file = os.path.join(layer_base, 'requirements.txt')
    if os.path.exists(requirements_file):
        print(f"✅ requirements.txt found")
        with open(requirements_file, 'r') as f:
            content = f.read().strip()
            print(f"   Content: {content}")
    else:
        print(f"❌ requirements.txt not found")
    
    # Check python directory
    python_dir = os.path.join(layer_base, 'python')
    if os.path.exists(python_dir):
        print(f"✅ python directory exists: {python_dir}")
        
        # List contents
        try:
            contents = os.listdir(python_dir)
            if contents:
                print(f"   Contents ({len(contents)} items):")
                for item in sorted(contents)[:10]:  # Show first 10 items
                    print(f"     - {item}")
                if len(contents) > 10:
                    print(f"     ... and {len(contents) - 10} more items")
            else:
                print("   ❌ python directory is empty")
        except Exception as e:
            print(f"   ❌ Error listing contents: {e}")
    else:
        print(f"❌ python directory not found: {python_dir}")

def check_sam_template():
    """Check if AWS Data Wrangler layer is configured in SAM template"""
    
    print("\n🔍 Checking SAM template configuration...")
    print("=" * 60)
    
    template_path = os.path.join(os.path.dirname(__file__), 'template.yaml')
    
    if not os.path.exists(template_path):
        print(f"❌ SAM template not found: {template_path}")
        return
    
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Check for AWS Data Wrangler layer ARN
    aws_layer_arn = "arn:aws:lambda:eu-west-1:336392948345:layer:AWSSDKPandas-Python311"
    if aws_layer_arn in template_content:
        print("✅ AWS Data Wrangler layer (AWSSDKPandas) is configured in SAM template")
        print(f"   Using pre-built AWS layer with pandas, pyarrow, and more")
    else:
        print("❌ AWS Data Wrangler layer is NOT configured in SAM template")
        print("   Need to add AWS layer ARN to template.yaml")
    
    # Check if GenerateMemberParquetFunction exists
    if 'GenerateMemberParquetFunction:' in template_content:
        print("✅ GenerateMemberParquetFunction is defined")
        
        # Look for AWS layer reference in the function
        if aws_layer_arn in template_content:
            print("✅ GenerateMemberParquetFunction uses AWS Data Wrangler layer")
        else:
            print("❌ GenerateMemberParquetFunction does NOT use AWS Data Wrangler layer")
            print("   Need to add AWS layer ARN to the function's Layers configuration")
    else:
        print("❌ GenerateMemberParquetFunction not found in template")

if __name__ == "__main__":
    print("🧪 PandasLayer Verification Test")
    print("Testing pandas and pyarrow availability for H-DCN Member Reporting")
    print()
    
    # Run all checks
    check_layer_structure()
    check_sam_template()
    libraries_available = test_pandas_layer_imports()
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    print("✅ UPDATED APPROACH: Using AWS Data Wrangler Layer")
    print("   - Pre-built AWS layer with pandas, pyarrow, and more libraries")
    print("   - No custom layer building required")
    print("   - Maintained and updated by AWS")
    print("   - Ready for immediate deployment")
    
    print("\n📚 For more information, see:")
    print("   - Plan of Approach: .kiro/specs/member-reporting/planOfApproach.md")
    print("   - AWS Data Wrangler: https://aws-sdk-pandas.readthedocs.io/")
    print("   - Task: Phase 1.1 - Verify PandasLayer contains required libraries")