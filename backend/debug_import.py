#!/usr/bin/env python3
import sys
import os

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path[:3])  # Show first 3 entries

# Test basic file reading
try:
    with open('handler/get_events/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"✅ File read successfully, length: {len(content)}")
    print(f"First 50 characters: {repr(content[:50])}")
except Exception as e:
    print(f"❌ File read failed: {e}")

# Test if there are any null bytes
try:
    with open('handler/get_events/app.py', 'rb') as f:
        binary_content = f.read()
    null_count = binary_content.count(b'\x00')
    print(f"Null bytes in file: {null_count}")
    if null_count > 0:
        print("Null byte positions:", [i for i, b in enumerate(binary_content) if b == 0])
except Exception as e:
    print(f"❌ Binary read failed: {e}")

# Test compilation
try:
    with open('handler/get_events/app.py', 'r', encoding='utf-8') as f:
        source_code = f.read()
    compiled = compile(source_code, 'handler/get_events/app.py', 'exec')
    print("✅ Code compiled successfully")
except Exception as e:
    print(f"❌ Compilation failed: {e}")
    print(f"Error type: {type(e)}")