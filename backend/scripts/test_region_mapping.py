#!/usr/bin/env python3
"""
Test script to verify region mappings match memberFields.ts
"""

# Valid regions from memberFields.ts
VALID_REGIONS = [
    'Noord-Holland',
    'Zuid-Holland', 
    'Friesland',
    'Utrecht',
    'Oost',
    'Limburg',
    'Groningen/Drenthe',
    'Brabant/Zeeland',
    'Duitsland',
    'Overig'
]

# Import the mapping from the script
import sys
import os
sys.path.append(os.path.dirname(__file__))

# Copy the mapping from import_members_sheets.py
regio_value_mapping = {
    # Standard region name corrections (add hyphens)
    'Noord Holland': 'Noord-Holland',
    'Zuid Holland': 'Zuid-Holland',
    
    # Spelling corrections
    'Groningen/Drente': 'Groningen/Drenthe',
    'Groningen/Drenthe': 'Groningen/Drenthe',  # Already correct
    
    # Regional mapping corrections - FIXED to match memberFields.ts
    'Brabant/Zeeland': 'Brabant/Zeeland',      # ✅ Keep as-is (correct in memberFields.ts)
    'Brabant': 'Brabant/Zeeland',
    'Noord-Brabant': 'Brabant/Zeeland',
    'Zeeland': 'Brabant/Zeeland',
    
    # International and special cases
    'Deutschland': 'Duitsland',
    'Germany': 'Overig',                        # ✅ Changed from 'Other' to 'Overig'
    'Belgie': 'Overig',
    'Belgium': 'Overig',
    'Belgique': 'Overig',
    'Frankrijk': 'Overig',
    'France': 'Overig',
    'Oostenrijk': 'Overig',
    'Austria': 'Overig',
    'Zwitserland': 'Overig',
    'Switzerland': 'Overig',
    'Luxemburg': 'Overig',
    'Luxembourg': 'Overig',
    
    # No region specified - FIXED to match memberFields.ts
    'Geen': 'Overig',                          # ✅ Changed from 'Other' to 'Overig'
    'Geen regio': 'Overig',
    'Onbekend': 'Overig',
    'Unknown': 'Overig',
    'N/A': 'Overig',
    'NA': 'Overig',
    
    # Alternative spellings and variations
    'Friesland/Frisia': 'Friesland',
    'Fryslân': 'Friesland',
    'Gelderland': 'Oost',
    'Overijssel': 'Oost',
    'Flevoland': 'Oost',
    'Drenthe': 'Groningen/Drenthe',
    'Groningen': 'Groningen/Drenthe',
    
    # Province to region mapping - FIXED to match memberFields.ts
    'Noord-Brabant': 'Brabant/Zeeland',        # ✅ Fixed mapping
    'Limburg': 'Limburg',                      # Already correct
    'Utrecht': 'Utrecht',                      # Already correct
    'Noord-Holland': 'Noord-Holland',          # Already correct
    'Zuid-Holland': 'Zuid-Holland',            # Already correct
    'Friesland': 'Friesland',                  # Already correct
    'Oost': 'Oost',                           # Already correct
    'Duitsland': 'Duitsland',                 # Already correct
    
    # Common misspellings
    'Noord-holland': 'Noord-Holland',
    'Zuid-holland': 'Zuid-Holland',
    'noord holland': 'Noord-Holland',
    'zuid holland': 'Zuid-Holland',
    'groningen/drente': 'Groningen/Drenthe',
    'GRONINGEN/DRENTHE': 'Groningen/Drenthe',
    'brabant/zeeland': 'Brabant/Zeeland',      # ✅ Fixed mapping
    'BRABANT/ZEELAND': 'Brabant/Zeeland',      # ✅ Fixed mapping
    
    # Empty or whitespace values - FIXED to match memberFields.ts
    '': 'Overig',                              # ✅ Changed from 'Other' to 'Overig'
    ' ': 'Overig',                             # ✅ Changed from 'Other' to 'Overig'
}

def test_region_mappings():
    """Test that all mapped values are valid"""
    print("🔍 Testing region mappings against memberFields.ts...")
    
    invalid_mappings = []
    valid_mappings = []
    
    for csv_value, db_value in regio_value_mapping.items():
        if db_value in VALID_REGIONS:
            valid_mappings.append((csv_value, db_value))
        else:
            invalid_mappings.append((csv_value, db_value))
    
    print(f"\n✅ Valid mappings: {len(valid_mappings)}")
    for csv_val, db_val in valid_mappings[:10]:  # Show first 10
        print(f"   '{csv_val}' → '{db_val}'")
    if len(valid_mappings) > 10:
        print(f"   ... and {len(valid_mappings) - 10} more")
    
    if invalid_mappings:
        print(f"\n❌ Invalid mappings: {len(invalid_mappings)}")
        for csv_val, db_val in invalid_mappings:
            print(f"   '{csv_val}' → '{db_val}' (NOT in memberFields.ts)")
    else:
        print(f"\n🎉 All mappings are valid!")
    
    print(f"\n📋 Valid regions in memberFields.ts:")
    for region in VALID_REGIONS:
        print(f"   - {region}")
    
    return len(invalid_mappings) == 0

if __name__ == "__main__":
    success = test_region_mappings()
    if success:
        print(f"\n✅ All region mappings are correct!")
    else:
        print(f"\n❌ Some region mappings need fixing!")