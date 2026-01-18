# Design Document: Member Reporting Performance

> **⚠️ DEVELOPMENT SPECIFICATION**
>
> This document describes the design for a NEW system to be developed. These features are NOT yet implemented in production. The current production system uses S3 Parquet files for member reporting. This design will replace that system.

## Overview

This design implements a simplified regional filtering system to improve member reporting performance. The system replaces the current S3 Parquet approach with a backend regional filtering API that sends only relevant data to users based on their JWT permissions. Browser session storage provides automatic caching during user sessions, eliminating the need for complex backend cache management.

**Key Design Principles:**

- **Simplicity**: No backend caching infrastructure, no TTL management
- **Security**: Users only receive data they're permitted to access
- **Performance**: 70-90% reduction in data transfer for regional users
- **Maintainability**: Remove Parquet system, reduce code complexity
- **Reuse Existing Infrastructure**: Leverage all existing systems (Auth Layer, SAM template, frontend utilities)

## Existing Infrastructure Reuse

**This design leverages all existing H-DCN infrastructure:**

### Backend Infrastructure

- ✅ **Auth Layer** (`backend/shared/auth_utils.py`):
  - `extract_user_credentials()` - JWT validation
  - `validate_permissions_with_regions()` - Regional permission checking
  - `create_success_response()` / `create_error_response()` - Standard responses
  - `cors_headers()` - CORS configuration
  - `log_successful_access()` - Audit logging

- ✅ **SAM Template** (`template.yaml`):
  - Existing Lambda function patterns
  - API Gateway integration
  - DynamoDB table references
  - IAM roles and policies
  - Environment variables

- ✅ **DynamoDB**:
  - Existing Members table
  - No schema changes needed
  - Reuse existing scan patterns

### Frontend Infrastructure

- ✅ **Calculated Fields** (`frontend/src/utils/calculatedFields.ts`):
  - `computeCalculatedFieldsForArray()` - Compute korte_naam, leeftijd, etc.
  - All existing compute functions
  - No changes needed

- ✅ **Member Fields Config** (`frontend/src/config/memberFields.ts`):
  - Field definitions and permissions
  - Status enum values
  - Validation rules

- ✅ **Authentication** (`frontend/src/hooks/useAuth.ts`):
  - JWT token management
  - Permission checking
  - User role access

- ✅ **API Utilities**:
  - Existing fetch patterns
  - Error handling
  - CORS headers

**What's New:**

- ❌ Remove: Parquet generation/download handlers
- ✅ Add: One new Lambda handler (`get_members_filtered`)
- ✅ Add: One new frontend service (`MemberDataService.ts`)
- ✅ Add: Session storage caching logic

**No Breaking Changes:**

- All existing member management functions continue to work
- No database schema changes
- No authentication changes
- No frontend component changes (except member reporting page)

## Architecture

### High-Level Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Browser   │         │   API Gateway    │         │  DynamoDB   │
│             │         │                  │         │   Members   │
│  React App  │◄───────►│  Lambda Handler  │◄───────►│    Table    │
│             │  HTTPS  │  (Regional API)  │         │             │
│             │         │                  │         │             │
└─────────────┘         └──────────────────┘         └─────────────┘
      │
      │ Session Storage
      │ (Browser Cache)
      ▼
┌─────────────┐
│   Session   │
│   Storage   │
│  (Cached    │
│   Members)  │
└─────────────┘
```

### Request Flow

**First Load (Cache Miss):**

1. User opens member reporting page
2. Frontend checks session storage → empty
3. Frontend calls `/api/members` with JWT token
4. Lambda extracts region from JWT (e.g., "Regio_Utrecht")
5. Lambda scans DynamoDB (1500 members)
6. Lambda filters by region (returns ~200 members for regional users, 1500 for Regio_All)
7. Frontend receives filtered JSON data
8. Frontend stores in session storage
9. Frontend displays member list

**Subsequent Navigation (Cache Hit):**

1. User navigates within reporting interface
2. Frontend checks session storage → data exists
3. Frontend uses cached data (instant load)
4. No backend call needed

**Manual Refresh:**

1. CRUD user clicks "Refresh Data" button
2. Frontend clears session storage
3. Frontend calls `/api/members` (same as first load)
4. Frontend updates display with fresh data

## Components and Interfaces

### 1. Backend: Regional Filtering Lambda

**File**: `backend/handler/get_members_filtered/app.py`

**Purpose**: Fetch all members from DynamoDB and filter by user's region before sending to frontend

**Important**: Backend sends only raw member data from DynamoDB. Calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) are computed in the frontend using the existing `calculatedFields.ts` system.

**Interface**:

```python
# HTTP Request
GET /api/members
Headers:
  Authorization: Bearer <JWT_TOKEN>
  X-Enhanced-Groups: <COGNITO_GROUPS>

# HTTP Response (Success)
{
  "success": true,
  "data": [
    {
      // Raw member data from DynamoDB (no calculated fields)
      "lidnummer": "12345",
      "voornaam": "Jan",
      "tussenvoegsel": "van",
      "achternaam": "Jansen",
      "email": "jan@example.com",
      "regio": "Utrecht",
      "status": "Actief",
      "geboortedatum": "1978-09-26",
      "tijdstempel": "2018-04-01",
      // ... all other raw member fields from DynamoDB
      // NOTE: Calculated fields (korte_naam, leeftijd, etc.) are NOT included
      // They will be computed by frontend using calculatedFields.ts
    },
    // ... more members
  ],
  "metadata": {
    "total_count": 187,
    "region": "Utrecht",
    "timestamp": "2026-01-17T10:30:00Z"
  }
}

# HTTP Response (Error)
{
  "success": false,
  "error": "Authentication failed",
  "details": "Invalid JWT token"
}
```

**Key Functions**:

```python
def lambda_handler(event, context):
    """
    Main handler for regional member data API
    """
    # 1. Extract user credentials from JWT
    user_email, user_roles, auth_error = extract_user_credentials(event)

    # 2. Validate permissions (any member permission required)
    is_authorized, auth_error, regional_info = validate_permissions_with_regions(
        user_roles,
        ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete'],
        user_email
    )

    # 3. Load all members from DynamoDB
    members = load_members_from_dynamodb()

    # 4. Filter by user's region
    filtered_members = filter_members_by_region(members, regional_info)

    # 5. Return filtered data
    return create_success_response({
        'success': True,
        'data': filtered_members,
        'metadata': {
            'total_count': len(filtered_members),
            'region': regional_info.get('region', 'All'),
            'timestamp': datetime.utcnow().isoformat()
        }
    })

def convert_dynamodb_to_python(item):
    """
    Convert DynamoDB item to Python native types
    CRITICAL: Handles Decimal conversion to avoid JSON serialization errors

    DynamoDB returns numbers as Decimal objects which cannot be JSON serialized.
    This function converts Decimals to int or float as appropriate.

    Args:
        item: DynamoDB item dictionary

    Returns:
        Dictionary with Python native types
    """
    from decimal import Decimal

    converted = {}
    for key, value in item.items():
        if isinstance(value, Decimal):
            # Convert Decimal to int or float
            if value % 1 == 0:
                converted[key] = int(value)
            else:
                converted[key] = float(value)
        elif isinstance(value, dict):
            converted[key] = convert_dynamodb_to_python(value)
        elif isinstance(value, list):
            converted[key] = [
                convert_dynamodb_to_python(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            converted[key] = value
    return converted

def load_members_from_dynamodb():
    """
    Scan all members from DynamoDB
    Returns: List of member dictionaries with Python native types
    """
    table = dynamodb.Table(MEMBERS_TABLE_NAME)
    response = table.scan()
    members = response['Items']

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        members.extend(response['Items'])

    # CRITICAL: Convert Decimal types to int/float for JSON serialization
    return [convert_dynamodb_to_python(member) for member in members]

def filter_members_by_region(members, regional_info):
    """
    Filter members based on user's regional permissions

    Regional users only see members from their assigned region
    Regio_All users see all members from all regions

    Args:
        members: List of all member dictionaries
        regional_info: Dict with 'region' key (e.g., {'region': 'Utrecht'} or {'region': 'All'})

    Returns:
        List of filtered member dictionaries
    """
    region = regional_info.get('region', 'All')

    # Regio_All users get all members (no filtering)
    if region == 'All':
        return members

    # Regional users get only their region's members
    return [
        m for m in members
        if m.get('regio') == region
    ]
```

### 2. Frontend: Member Data Service

**File**: `frontend/src/services/MemberDataService.ts`

**Purpose**: Manage member data fetching, calculated field computation, and session storage caching

**Dependencies**:

- `computeCalculatedFieldsForArray` from `../utils/calculatedFields.ts` - computes korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar

**Interface**:

```typescript
export interface Member {
  lidnummer: string;
  voornaam: string;
  achternaam: string;
  email: string;
  regio: string;
  status: string;
  // ... all member fields
}

export interface MemberDataResponse {
  success: boolean;
  data: Member[];
  metadata: {
    total_count: number;
    region: string;
    timestamp: string;
  };
}

export class MemberDataService {
  private static STORAGE_KEY = "hdcn_member_data";
  private static STORAGE_TIMESTAMP_KEY = "hdcn_member_data_timestamp";

  /**
   * Fetch members from backend API
   * Automatically computes calculated fields and caches in session storage
   */
  static async fetchMembers(forceRefresh: boolean = false): Promise<Member[]> {
    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cached = this.getCachedMembers();
      if (cached) {
        console.log("Using cached member data");
        return cached;
      }
    }

    // Fetch from backend
    console.log("Fetching fresh member data from backend");
    const response = await fetch("/api/members", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${getJWTToken()}`,
        "X-Enhanced-Groups": getEnhancedGroups(),
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch members: ${response.statusText}`);
    }

    const data: MemberDataResponse = await response.json();

    // IMPORTANT: Compute calculated fields using existing calculatedFields.ts system
    // Backend sends only raw data, frontend computes: korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar
    const membersWithCalculatedFields = computeCalculatedFieldsForArray(
      data.data,
    );

    // Cache in session storage (with calculated fields)
    this.cacheMembers(membersWithCalculatedFields);

    return membersWithCalculatedFields;
  }

  /**
   * Get cached members from session storage
   */
  private static getCachedMembers(): Member[] | null {
    try {
      const cached = sessionStorage.getItem(this.STORAGE_KEY);
      if (!cached) return null;

      return JSON.parse(cached);
    } catch (error) {
      console.error("Error reading from session storage:", error);
      return null;
    }
  }

  /**
   * Cache members in session storage
   */
  private static cacheMembers(members: Member[]): void {
    try {
      sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify(members));
      sessionStorage.setItem(
        this.STORAGE_TIMESTAMP_KEY,
        new Date().toISOString(),
      );
    } catch (error) {
      console.error("Error writing to session storage:", error);
      // Continue without caching - not critical
    }
  }

  /**
   * Clear cached members (for manual refresh)
   */
  static clearCache(): void {
    try {
      sessionStorage.removeItem(this.STORAGE_KEY);
      sessionStorage.removeItem(this.STORAGE_TIMESTAMP_KEY);
    } catch (error) {
      console.error("Error clearing session storage:", error);
    }
  }

  /**
   * Refresh members (clear cache and fetch fresh)
   */
  static async refreshMembers(): Promise<Member[]> {
    this.clearCache();
    return this.fetchMembers(true);
  }
}
```

### 3. Frontend: Member List Component

**File**: `frontend/src/components/MemberList.tsx`

**Purpose**: Display member list with filtering and refresh capability

**Key Features**:

```typescript
export const MemberList: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [filteredMembers, setFilteredMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MemberFilters>({});

  const { hasPermission } = useAuth();
  const canRefresh = hasPermission(['members_update', 'members_create']);

  // Load members on mount
  useEffect(() => {
    loadMembers();
  }, []);

  const loadMembers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await MemberDataService.fetchMembers();
      setMembers(data);
      setFilteredMembers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await MemberDataService.refreshMembers();
      setMembers(data);
      setFilteredMembers(data);
      toast({
        title: 'Data refreshed',
        status: 'success',
        duration: 2000
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters: MemberFilters) => {
    setFilters(newFilters);
    const filtered = applyFilters(members, newFilters);
    setFilteredMembers(filtered);
  };

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Heading>Members ({filteredMembers.length} / {members.length})</Heading>
        {canRefresh && (
          <Button
            leftIcon={<RepeatIcon />}
            onClick={handleRefresh}
            isLoading={loading}
            colorScheme="blue"
          >
            Refresh Data
          </Button>
        )}
      </HStack>

      {error && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          {error}
        </Alert>
      )}

      {loading ? (
        <Center py={10}>
          <Spinner size="xl" />
        </Center>
      ) : (
        <>
          <MemberFilters onChange={handleFilterChange} />
          <MemberTable members={filteredMembers} />
        </>
      )}
    </Box>
  );
};
```

### 4. Frontend: Member Filters Component

**File**: `frontend/src/components/MemberFilters.tsx`

**Purpose**: Provide filtering UI for all member columns

**Interface**:

```typescript
export interface MemberFilters {
  status?: string;
  regio?: string;
  lidmaatschap?: string;
  searchText?: string;
  birthdayMonth?: number;
  // ... filters for any column
}

export const MemberFilters: React.FC<{
  onChange: (filters: MemberFilters) => void;
}> = ({ onChange }) => {
  const [filters, setFilters] = useState<MemberFilters>({});

  const updateFilter = (key: keyof MemberFilters, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onChange(newFilters);
  };

  return (
    <Box p={4} borderWidth={1} borderRadius="md" mb={4}>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
        {/* Status Filter */}
        <FormControl>
          <FormLabel>Status</FormLabel>
          <Select
            placeholder="All"
            value={filters.status || ''}
            onChange={(e) => updateFilter('status', e.target.value)}
          >
            <option value="Actief">Actief</option>
            <option value="Inactief">Inactief</option>
          </Select>
        </FormControl>

        {/* Region Filter */}
        <FormControl>
          <FormLabel>Region</FormLabel>
          <Select
            placeholder="All"
            value={filters.regio || ''}
            onChange={(e) => updateFilter('regio', e.target.value)}
          >
            <option value="Utrecht">Utrecht</option>
            <option value="Zuid-Holland">Zuid-Holland</option>
            {/* ... all regions */}
          </Select>
        </FormControl>

        {/* Search Text */}
        <FormControl>
          <FormLabel>Search</FormLabel>
          <Input
            placeholder="Name, email, phone..."
            value={filters.searchText || ''}
            onChange={(e) => updateFilter('searchText', e.target.value)}
          />
        </FormControl>

        {/* Birthday Month */}
        <FormControl>
          <FormLabel>Birthday Month</FormLabel>
          <Select
            placeholder="All"
            value={filters.birthdayMonth || ''}
            onChange={(e) => updateFilter('birthdayMonth', parseInt(e.target.value))}
          >
            <option value="1">January</option>
            <option value="2">February</option>
            {/* ... all months */}
          </Select>
        </FormControl>
      </SimpleGrid>
    </Box>
  );
};

/**
 * Apply filters to member list
 */
export function applyFilters(members: Member[], filters: MemberFilters): Member[] {
  return members.filter(member => {
    // Status filter
    if (filters.status && member.status !== filters.status) {
      return false;
    }

    // Region filter
    if (filters.regio && member.regio !== filters.regio) {
      return false;
    }

    // Search text (name, email, phone)
    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      const matchesSearch =
        member.voornaam?.toLowerCase().includes(searchLower) ||
        member.achternaam?.toLowerCase().includes(searchLower) ||
        member.email?.toLowerCase().includes(searchLower) ||
        member.telefoon?.includes(searchLower);

      if (!matchesSearch) return false;
    }

    // Birthday month filter
    if (filters.birthdayMonth) {
      const birthDate = new Date(member.geboortedatum);
      if (birthDate.getMonth() + 1 !== filters.birthdayMonth) {
        return false;
      }
    }

    return true;
  });
}
```

## Data Models

### Member Data Model

**Source**: DynamoDB Members table (raw data) + Frontend calculated fields

**Backend Response**: Contains only raw fields from DynamoDB
**Frontend Processing**: Adds calculated fields using `calculatedFields.ts`

**Fields**:

```typescript
interface Member {
  // Core identification
  lidnummer: string; // Member number (primary key)
  voornaam: string; // First name
  tussenvoegsel?: string; // Middle name/prefix
  achternaam: string; // Last name

  // Contact information
  email: string;
  telefoon?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  land?: string;

  // Membership details
  status: string; // "Actief" | "Inactief"
  regio: string; // Region (e.g., "Utrecht", "Zuid-Holland")
  lidmaatschap: string; // Membership type
  clubblad: string; // Newsletter preference
  tijdstempel: string; // Membership start date (ISO 8601)
  geboortedatum: string; // Birth date (ISO 8601)

  // Motorcycle information (optional)
  motor_merk?: string;
  motor_type?: string;
  motor_bouwjaar?: string;
  motor_kenteken?: string;

  // Calculated fields (computed in frontend using calculatedFields.ts)
  // These fields are NOT sent by backend, they are computed after fetching
  korte_naam?: string; // Full name (voornaam + tussenvoegsel + achternaam)
  leeftijd?: number; // Age in years (from geboortedatum)
  verjaardag?: string; // Birthday in Dutch format (e.g., "september 26")
  jaren_lid?: number; // Years of membership (from tijdstempel)
  aanmeldingsjaar?: number; // Year of membership start (from tijdstempel)
}
```

**Calculated Fields Processing**:

```typescript
// After fetching from backend, frontend computes calculated fields:
import { computeCalculatedFieldsForArray } from "../utils/calculatedFields";

const rawMembers = await fetchFromBackend(); // Raw data from DynamoDB
const membersWithCalculatedFields = computeCalculatedFieldsForArray(rawMembers);
// Now members have korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar
```

### Regional Info Model

**Source**: Extracted from JWT token by auth layer

**Structure**:

```typescript
interface RegionalInfo {
  region: string; // "All" | "Utrecht" | "Zuid-Holland" | etc.
  regions: string[]; // List of all regions user has access to
}
```

## Error Handling

### Backend Error Handling

**Authentication Errors**:

```python
# Missing or invalid JWT token
if auth_error:
    return create_error_response(401, 'Authentication required', {
        'details': 'Valid JWT token required'
    })

# Insufficient permissions
if not is_authorized:
    return create_error_response(403, 'Access denied', {
        'details': 'Member read permission required',
        'required_permissions': ['members_read', 'members_export', 'members_create', 'members_update', 'members_delete']
    })
```

**Database Errors**:

```python
try:
    members = load_members_from_dynamodb()
except Exception as e:
    logger.error(f"DynamoDB error: {str(e)}")
    return create_error_response(500, 'Database error', {
        'details': 'Failed to load member data'
    })
```

### Frontend Error Handling

**Network Errors**:

```typescript
try {
  const members = await MemberDataService.fetchMembers();
  setMembers(members);
} catch (error) {
  if (error.message.includes("401")) {
    setError("Authentication failed. Please log in again.");
  } else if (error.message.includes("403")) {
    setError("You do not have permission to view member data.");
  } else if (error.message.includes("500")) {
    setError("Server error. Please try again later.");
  } else {
    setError("Failed to load member data. Please check your connection.");
  }
}
```

**Session Storage Errors**:

```typescript
// Session storage failures are non-critical
try {
  sessionStorage.setItem(key, value);
} catch (error) {
  console.error("Session storage failed:", error);
  // Continue without caching - app still works
}
```

## Testing Strategy

### Unit Tests

**Backend Tests** (`backend/handler/get_members_filtered/test_app.py`):

```python
def test_filter_members_by_region_all():
    """Test that Regio_All users get all members from all regions"""
    members = [
        {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
        {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Inactief'},
        {'lidnummer': '3', 'regio': 'Noord-Holland', 'status': 'Verwijderd'}
    ]
    regional_info = {'region': 'All'}

    result = filter_members_by_region(members, regional_info)

    assert len(result) == 3  # All members returned

def test_filter_members_by_region_specific():
    """Test that regional users get only members from their region"""
    members = [
        {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
        {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Actief'},
        {'lidnummer': '3', 'regio': 'Utrecht', 'status': 'Opgezegd'},
        {'lidnummer': '4', 'regio': 'Utrecht', 'status': 'Inactief'},
        {'lidnummer': '5', 'regio': 'Utrecht', 'status': 'wachtRegio'}
    ]
    regional_info = {'region': 'Utrecht'}

    result = filter_members_by_region(members, regional_info)

    assert len(result) == 4  # All Utrecht members regardless of status
    assert all(m['regio'] == 'Utrecht' for m in result)
    assert '2' not in [m['lidnummer'] for m in result]  # Zuid-Holland member excluded

def test_filter_members_all_statuses_included():
    """Test that all statuses are included for regional users"""
    members = [
        {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
        {'lidnummer': '2', 'regio': 'Utrecht', 'status': 'Opgezegd'},
        {'lidnummer': '3', 'regio': 'Utrecht', 'status': 'Inactief'},
        {'lidnummer': '4', 'regio': 'Utrecht', 'status': 'Verwijderd'},
        {'lidnummer': '5', 'regio': 'Utrecht', 'status': 'Geschorst'}
    ]
    regional_info = {'region': 'Utrecht'}

    result = filter_members_by_region(members, regional_info)

    assert len(result) == 5  # All statuses included

def test_authentication_required():
    """Test that requests without JWT are rejected"""
    event = {'httpMethod': 'GET'}  # No Authorization header

    response = lambda_handler(event, None)

    assert response['statusCode'] == 401
```

**Frontend Tests** (`frontend/src/services/__tests__/MemberDataService.test.ts`):

```typescript
describe("MemberDataService", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  test("fetchMembers caches data in session storage", async () => {
    const mockMembers = [
      { lidnummer: "1", voornaam: "Jan", achternaam: "Jansen" },
    ];

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockMembers }),
    });

    await MemberDataService.fetchMembers();

    const cached = sessionStorage.getItem("hdcn_member_data");
    expect(cached).toBeTruthy();
    expect(JSON.parse(cached!)).toEqual(mockMembers);
  });

  test("fetchMembers uses cache on second call", async () => {
    const mockMembers = [
      { lidnummer: "1", voornaam: "Jan", achternaam: "Jansen" },
    ];

    // First call - should fetch from API
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockMembers }),
    });

    await MemberDataService.fetchMembers();
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Second call - should use cache
    await MemberDataService.fetchMembers();
    expect(global.fetch).toHaveBeenCalledTimes(1); // Still 1, not 2
  });

  test("refreshMembers clears cache and fetches fresh", async () => {
    // Set up cache
    sessionStorage.setItem(
      "hdcn_member_data",
      JSON.stringify([{ lidnummer: "1" }]),
    );

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: [{ lidnummer: "2" }] }),
    });

    await MemberDataService.refreshMembers();

    expect(global.fetch).toHaveBeenCalled();
    const cached = JSON.parse(sessionStorage.getItem("hdcn_member_data")!);
    expect(cached[0].lidnummer).toBe("2");
  });
});
```

**Filter Tests** (`frontend/src/components/__tests__/MemberFilters.test.ts`):

```typescript
describe("applyFilters", () => {
  const members: Member[] = [
    { lidnummer: "1", voornaam: "Jan", status: "Actief", regio: "Utrecht" },
    {
      lidnummer: "2",
      voornaam: "Piet",
      status: "Inactief",
      regio: "Zuid-Holland",
    },
    { lidnummer: "3", voornaam: "Klaas", status: "Actief", regio: "Utrecht" },
  ];

  test("filters by status", () => {
    const result = applyFilters(members, { status: "Actief" });
    expect(result).toHaveLength(2);
    expect(result.every((m) => m.status === "Actief")).toBe(true);
  });

  test("filters by region", () => {
    const result = applyFilters(members, { regio: "Utrecht" });
    expect(result).toHaveLength(2);
    expect(result.every((m) => m.regio === "Utrecht")).toBe(true);
  });

  test("filters by search text", () => {
    const result = applyFilters(members, { searchText: "jan" });
    expect(result).toHaveLength(1);
    expect(result[0].voornaam).toBe("Jan");
  });

  test("combines multiple filters with AND logic", () => {
    const result = applyFilters(members, {
      status: "Actief",
      regio: "Utrecht",
    });
    expect(result).toHaveLength(2);
    expect(
      result.every((m) => m.status === "Actief" && m.regio === "Utrecht"),
    ).toBe(true);
  });
});
```

### Integration Tests

**End-to-End Flow Test**:

```typescript
describe('Member Reporting Integration', () => {
  test('complete user flow: load, filter, refresh', async () => {
    // 1. Load member list
    render(<MemberList />);

    await waitFor(() => {
      expect(screen.getByText(/Members/)).toBeInTheDocument();
    });

    // 2. Apply filter
    const statusFilter = screen.getByLabelText('Status');
    fireEvent.change(statusFilter, { target: { value: 'Actief' } });

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      expect(rows.length).toBeGreaterThan(0);
    });

    // 3. Refresh data
    const refreshButton = screen.getByText('Refresh Data');
    fireEvent.click(refreshButton);

    await waitFor(() => {
      expect(screen.getByText('Data refreshed')).toBeInTheDocument();
    });
  });
});
```

## Implementation Notes

### Critical: DynamoDB Decimal Handling

**Problem**: DynamoDB returns numeric values as `Decimal` objects (from Python's `decimal` module), which cannot be JSON serialized directly. This will cause `TypeError: Object of type Decimal is not JSON serializable` errors.

**Solution**: The `convert_dynamodb_to_python()` function converts all Decimal values to native Python int or float:

```python
if isinstance(value, Decimal):
    if value % 1 == 0:
        converted[key] = int(value)  # Whole numbers → int
    else:
        converted[key] = float(value)  # Decimals → float
```

**Why This Matters**:

- DynamoDB stores numbers as Decimals for precision
- JSON.dumps() cannot serialize Decimal objects
- Must convert before returning from Lambda
- Existing Parquet handler already does this (reuse the pattern)

**Testing**:

- Test with members that have numeric fields
- Verify JSON serialization works
- Check that no Decimal objects leak through

### Performance Considerations

**DynamoDB Scan Performance**:

- Scanning 1500 members takes ~200-500ms
- Acceptable for this use case (infrequent access)
- If table grows significantly (>10,000 members), consider:
  - Adding GSI for region-based queries
  - Implementing pagination
  - Using DynamoDB Streams for cache invalidation

**Session Storage Limits**:

- Browser session storage limit: ~5-10MB
- 1500 members in JSON: ~500KB-1MB
- Well within limits, no concern

**Frontend Filtering Performance**:

- Filtering 1500 members in JavaScript: <50ms
- Acceptable for real-time filtering
- No optimization needed

### Security Considerations

**Regional Data Isolation**:

- Backend enforces regional filtering
- Frontend never receives data outside user's permissions
- Even if frontend is compromised, user can't access other regions' data

**JWT Validation**:

- All requests validated by auth layer
- JWT signature verified
- Expired tokens rejected
- Regional permissions extracted from JWT claims

**Session Storage Security**:

- Session storage is per-tab, not shared between tabs
- Cleared when browser tab closes
- Not accessible to other domains (same-origin policy)
- No sensitive data (already filtered by permissions)

### Migration from Parquet System

**Cleanup Steps**:

1. Remove Lambda functions:
   - `backend/handler/generate_member_parquet/`
   - `backend/handler/download_parquet/`

2. Remove API Gateway endpoints:
   - `POST /analytics/generate-parquet`
   - `GET /analytics/download-parquet/{filename}`

3. Remove S3 files:
   - Delete `s3://my-hdcn-bucket/analytics/parquet/members/`

4. Update CloudFormation/SAM template:
   - Remove `GenerateMemberParquetFunction` resource
   - Remove `DownloadParquetFunction` resource
   - Remove associated IAM roles and policies

5. Update frontend:
   - Remove Parquet-related UI buttons
   - Remove `ParquetDataService.ts`
   - Remove `useParquetData.ts` hook
   - Update member reporting page to use new `MemberDataService`

## Deployment Plan

> **Note**: This deployment plan is for developing a new system that will replace the existing S3 Parquet system currently in production.

**Phase 1: Development Environment Setup** (Week 1)

1. Deploy new Lambda function: `get_members_filtered` to development
2. Add API Gateway endpoint: `GET /api/members` in development
3. Test with Postman/curl
4. Verify regional filtering works correctly
5. Run unit tests and integration tests

**Phase 2: Frontend Development** (Week 2)

1. Add `MemberDataService.ts`
2. Update `MemberList` component
3. Add refresh button for CRUD users
4. Test in development environment
5. Verify session storage caching works

**Phase 3: Integration Testing** (Week 3)

1. End-to-end testing in development
2. Performance testing (load times, filter response)
3. Security testing (regional isolation)
4. User acceptance testing with key stakeholders
5. Fix any issues found

**Phase 4: Production Deployment** (Week 4)

1. Deploy backend Lambda to production
2. Deploy frontend to production
3. Monitor performance and errors
4. Gather user feedback
5. Verify new system works correctly

**Phase 5: Remove Old Parquet System** (Week 5)

> **Important**: Only proceed with this phase after confirming the new system is stable in production.

1. Remove Parquet Lambda functions from production:
   - `backend/handler/generate_member_parquet/`
   - `backend/handler/download_parquet/`
2. Remove Parquet API Gateway endpoints:
   - `POST /analytics/generate-parquet`
   - `GET /analytics/download-parquet/{filename}`
3. Clean up S3 storage:
   - Delete `s3://my-hdcn-bucket/analytics/parquet/members/`
4. Update CloudFormation/SAM template:
   - Remove `GenerateMemberParquetFunction` resource
   - Remove `DownloadParquetFunction` resource
   - Remove associated IAM roles and policies
5. Remove Parquet-related frontend code:
   - Remove Parquet UI buttons
   - Remove `ParquetDataService.ts`
   - Remove `useParquetData.ts` hook
6. Update documentation to reflect the new system

## Success Metrics

**Performance Metrics**:

- Regional user load time: <2 seconds (target: 1 second)
- Regio_All user load time: <3 seconds (target: 2 seconds)
- Filter response time: <200ms
- Cache hit rate: >80% (after first load)

**User Experience Metrics**:

- Error rate: <1%
- User satisfaction: Positive feedback on speed improvement
- Support tickets: No increase in member reporting issues

**Technical Metrics**:

- Lambda execution time: <1 second
- DynamoDB scan time: <500ms
- API Gateway latency: <100ms
- Code reduction: ~1000 lines removed (Parquet system)
