#!/usr/bin/env python3
"""
Add AuthLayer to all Lambda functions in template.yaml that are missing it
"""

import re

# Read the template
with open('backend/template.yaml', 'r') as f:
    content = f.read()

# Pattern to find Lambda functions without Layers
# Matches: Function definition -> Properties -> CodeUri/Handler/Runtime but NO Layers before Role/Events
pattern = r'(  \w+Function:\n    Type: AWS::Serverless::Function\n    Properties:\n      (?:CodeUri: [^\n]+\n      )?Handler: app\.lambda_handler\n      Runtime: python3\.11\n)(      (?!Layers:))'

def add_layers(match):
    """Add Layers property after Runtime"""
    before = match.group(1)
    after = match.group(2)
    return before + "      Layers:\n        - !Ref AuthLayer\n" + after

# Apply the replacement
new_content = re.sub(pattern, add_layers, content)

# Count how many were added
original_layers = content.count('Layers:')
new_layers = new_content.count('Layers:')
added = new_layers - original_layers

print(f"Added AuthLayer to {added} functions")

# Write back
with open('backend/template.yaml', 'w') as f:
    f.write(new_content)

print("✅ template.yaml updated")
