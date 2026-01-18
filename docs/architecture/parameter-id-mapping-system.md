# Parameter ID Mapping System - Critical Architecture Component

## Overview

The H-DCN application uses a sophisticated ID-to-name mapping system through the Parameters table that is **critical** for proper application functionality. This system was discovered during parameter system troubleshooting and explains many design decisions throughout the codebase.

## Key Discovery

The application stores **numeric IDs** in member records and other data, then uses the **Parameters table as a lookup** to convert these IDs to human-readable names for display and processing.

## Region Mapping System

### Current Region ID Mapping

```json
{
  "regio": [
    { "id": "1", "value": "Noord-Holland" },
    { "id": "2", "value": "Zuid-Holland" },
    { "id": "3", "value": "Friesland" },
    { "id": "4", "value": "Utrecht" },
    { "id": "5", "value": "Oost" },
    { "id": "6", "value": "Limburg" },
    { "id": "7", "value": "Groningen/Drente" },
    { "id": "8", "value": "Noord-Brabant/Zeeland" },
    { "id": "9", "value": "Duitsland" }
  ]
}
```

### How It's Used Throughout the System

#### 1. **Member Data Storage**

- Members have `regio: "1"` (not `regio: "Noord-Holland"`)
- Database stores efficient numeric IDs
- Parameter table provides human-readable names

#### 2. **Role-Based Permissions**

- Roles like `Regional_Chairman_Region1`
- `Members_Read_Region1`
- `hdcnRegio_1_Chairman`
- All reference the numeric region ID

#### 3. **Regional Access Control**

```typescript
// Code checks if user's region matches member's region
const regionMatch = role.match(/Region(\d+)/);
if (regionMatch) {
  const roleRegion = regionMatch[1]; // "1", "2", etc.
  return memberRegion === roleRegion;
}
```

## Other Parameter Mappings

### Membership Types

```json
{
  "lidmaatschap": [
    { "id": "1", "value": "Gewoon lid" },
    { "id": "2", "value": "Gezins lid" },
    { "id": "3", "value": "Gezins donateur zonder motor" },
    { "id": "4", "value": "Donateur zonder motor" },
    { "id": "1759323585672", "value": "Erelid" }
  ]
}
```

### Status Mapping (AI-Generated)

```json
{
  "statuslidmaatschap": [
    { "id": "1759321836837", "value": "Nieuwe aanmelding" },
    { "id": "1759321847566", "value": "Wacht op betaling" },
    { "id": "1759321856811", "value": "Actief" },
    { "id": "1759321877249", "value": "Heeft opgezegd" },
    { "id": "1759321901826", "value": "Wacht op regio" },
    { "id": "1759321928173", "value": "Wacht op Ledenadministratie" }
  ]
}
```

### Delivery Options (AI-Generated)

```json
{
  "leveropties": [
    { "id": "1759242906717", "value": "Verzenden per koerier", "parent": null },
    { "id": "1759242920936", "value": "5.0", "parent": "1759242906717" },
    { "id": "1759242945568", "value": "Ophalen op afspraak", "parent": null },
    { "id": "1759242951768", "value": "1.0", "parent": "1759242945568" },
    { "id": "1759242969071", "value": "Ophalen bij ALV", "parent": null },
    { "id": "1759242974270", "value": "0", "parent": "1759242969071" }
  ]
}
```

## Critical Dependencies

### 1. **Parameter System Must Always Work**

- If parameter loading fails, the entire application breaks
- Region names become unreadable
- Dropdowns become empty
- Role-based access control fails

### 2. **ID Consistency is Essential**

- Changing region IDs breaks existing member data
- Role permissions become invalid
- Historical data becomes unreadable

### 3. **Backup and Recovery**

- Parameter data must be backed up separately
- JSON file serves as emergency fallback
- DynamoDB table is the source of truth

## AI Tool Integration

### Parameters Created by AI Tools

Several parameters were created by AI tools during development:

- `statuslidmaatschap` - Member status workflow
- `leveropties` - Delivery options with pricing
- `productsubgroepen` - Product categorization
- Additional `Erelid` membership type

### Timestamp-Based IDs

AI-generated parameters often use timestamp-based IDs:

- `1759323585672` (Erelid)
- `1759321836837` (Nieuwe aanmelding)
- `1759242906717` (Verzenden per koerier)

## Best Practices

### 1. **Never Change Existing IDs**

- IDs are permanent references
- Create new entries instead of modifying existing ones
- Maintain backward compatibility

### 2. **Always Include ID Mapping**

- Every parameter category needs ID-to-value mapping
- JSON file must match DynamoDB structure exactly
- Test parameter loading after any changes

### 3. **Regional Permission Alignment**

- Region IDs must align with role naming conventions
- `Region1` = ID "1" = "Noord-Holland"
- Maintain consistency across all systems

## Troubleshooting

### Symptoms of Parameter System Failure

- Empty dropdowns in forms
- "undefined" region names in member lists
- Permission errors for regional users
- Console errors about parameter loading

### Recovery Steps

1. Check parameter JSON file exists and is valid
2. Verify DynamoDB Parameters table is accessible
3. Ensure ID mappings are consistent
4. Test parameter loading in browser console

## Future Considerations

### 1. **Parameter Management UI**

- Must preserve ID mappings when editing
- Should show both ID and value
- Needs validation to prevent ID conflicts

### 2. **Data Migration**

- Any region changes require careful member data migration
- Role updates across all affected users
- Historical data preservation

### 3. **Monitoring**

- Parameter loading should be monitored
- Alerts for parameter system failures
- Regular backup verification

## Conclusion

The parameter ID mapping system is a **critical architectural component** that enables:

- Efficient data storage (numeric IDs)
- Flexible display names (changeable without data migration)
- Complex role-based permissions (region-specific access)
- Hierarchical data structures (parent-child relationships)

Understanding this system is essential for:

- Debugging parameter-related issues
- Implementing new features safely
- Maintaining data integrity
- Ensuring proper access control
