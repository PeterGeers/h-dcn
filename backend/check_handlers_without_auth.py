#!/usr/bin/env python3
"""
Check which handlers don't have shared auth and explain why
"""

import os

def check_handler_purpose(handler_name, app_py_path):
    """Check what type of handler this is and why it might not need auth"""
    
    if not os.path.exists(app_py_path):
        return "No app.py file - not a functional handler"
    
    try:
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for Cognito trigger patterns
        if 'cognito' in handler_name.lower():
            if 'event.get(' in content and ('triggerSource' in content or 'userPoolId' in content):
                return "Cognito trigger - doesn't need user authentication (triggered by AWS Cognito)"
            
        # Check for specific patterns
        if 'def lambda_handler(event, context):' in content:
            # Check if it's a simple utility without auth needs
            if 'cors_headers()' in content and 'from shared.auth_utils import' not in content:
                return "Simple utility handler - may need auth added"
            elif 'triggerSource' in content:
                return "Cognito trigger - doesn't need user authentication"
            elif 'Records' in content and 'eventName' in content:
                return "Event-driven handler (S3, DynamoDB streams) - doesn't need user auth"
            else:
                return "Regular handler - should have auth"
        
        return "Unknown handler type"
        
    except Exception as e:
        return f"Error reading file: {str(e)}"

def main():
    print("🔍 Analyzing handlers without shared auth...")
    print("=" * 70)
    
    handlers_without_auth = []
    
    for item in os.listdir('handler'):
        if os.path.isdir(f'handler/{item}') and item != '__pycache__':
            app_py = f'handler/{item}/app.py'
            
            has_shared_auth = False
            if os.path.exists(app_py):
                try:
                    with open(app_py, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'from shared.auth_utils import' in content:
                            has_shared_auth = True
                except:
                    pass
            
            if not has_shared_auth:
                purpose = check_handler_purpose(item, app_py)
                handlers_without_auth.append((item, purpose))
                print(f"❌ {item}")
                print(f"   Purpose: {purpose}")
                print()
    
    print("=" * 70)
    print(f"📊 Total handlers without shared auth: {len(handlers_without_auth)}")
    
    # Categorize them
    cognito_triggers = []
    missing_files = []
    needs_auth = []
    utilities = []
    
    for handler, purpose in handlers_without_auth:
        if "Cognito trigger" in purpose:
            cognito_triggers.append(handler)
        elif "No app.py" in purpose:
            missing_files.append(handler)
        elif "should have auth" in purpose or "may need auth" in purpose:
            needs_auth.append(handler)
        else:
            utilities.append(handler)
    
    print(f"\n📋 Breakdown:")
    print(f"🔧 Cognito triggers (don't need auth): {len(cognito_triggers)}")
    for h in cognito_triggers:
        print(f"   - {h}")
    
    print(f"\n📁 Missing app.py files: {len(missing_files)}")
    for h in missing_files:
        print(f"   - {h}")
    
    print(f"\n⚠️ May need auth added: {len(needs_auth)}")
    for h in needs_auth:
        print(f"   - {h}")
    
    print(f"\n🛠️ Other utilities: {len(utilities)}")
    for h in utilities:
        print(f"   - {h}")

if __name__ == "__main__":
    main()