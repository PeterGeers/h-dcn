# Parameter Service Documentation

## Overview

The `parameterService.tsx` is a service layer that provides a simplified interface for accessing and managing H-DCN system parameters. It acts as a wrapper around the more complex `parameterStore.tsx` and provides React hooks for component integration.

## Architecture

```
parameterService.tsx (Service Layer)
    ↓
parameterStore.tsx (Storage Layer)
    ↓
ApiService → DynamoDB Parameters Table
    ↓
localStorage (Fallback/Cache)
    ↓
Default Values (Final Fallback)
```

## Core Functionality

### 1. Parameter Retrieval (`getParameters`)

**Purpose**: Fetch all parameters from the parameter store with automatic caching and fallback mechanisms.

**Implementation**:

```typescript
export const getParameters = async (): Promise<Parameters> => {
  try {
    await parameterStore.refresh(); // Force refresh to ensure latest data
    const params = await parameterStore.getParameters();
    return params;
  } catch (error) {
    throw new Error("Fout bij laden parameters: " + error.message);
  }
};
```

**Key Features**:

- Forces refresh to ensure latest data
- Comprehensive error handling with Dutch error messages
- Debug logging for troubleshooting
- Returns structured parameter data organized by category

### 2. Parameter Caching (`clearParameterCache`)

**Purpose**: Clear the parameter cache to force reload of fresh data.

**Implementation**:

```typescript
export const clearParameterCache = async (): Promise<void> => {
  await parameterStore.refresh();
};
```

**Use Cases**:

- After parameter updates to ensure UI reflects changes
- Troubleshooting data inconsistencies
- Manual cache invalidation

### 3. Parameter Persistence (`saveParameter`)

**Purpose**: Save or update individual parameters with automatic ID generation.

**Implementation**:

```typescript
export const saveParameter = async (
  category: string,
  value: any,
  id: string | null = null
): Promise<void> => {
  const parameters = await getParameters();

  if (!parameters[category]) {
    parameters[category] = [];
  }

  if (id) {
    // Update existing parameter
    const index = parameters[category].findIndex((item) => item.id === id);
    if (index !== -1) {
      parameters[category][index].value = value;
    }
  } else {
    // Add new parameter with auto-generated UUID
    const newId = crypto.randomUUID();
    parameters[category].push({ id: newId, value });
  }

  await parameterStore.saveParameters(parameters);
};
```

**Key Features**:

- Automatic UUID generation for new parameters
- Category-based organization
- Update existing or create new functionality
- Delegates to parameterStore for actual persistence

### 4. Parameter Deletion (`deleteParameter`)

**Purpose**: Remove parameters from a specific category.

**Implementation**:

```typescript
export const deleteParameter = async (
  category: string,
  id: string
): Promise<void> => {
  const parameters = await getParameters();

  if (parameters[category]) {
    parameters[category] = parameters[category].filter(
      (item) => item.id !== id
    );
  }

  await parameterStore.saveParameters(parameters);
};
```

**Key Features**:

- Safe deletion with existence checks
- Category-based filtering
- Automatic persistence after deletion

### 5. React Hook Integration (`useParameters`)

**Purpose**: Provide React components with reactive parameter data.

**Implementation**:

```typescript
export const useParameters = (category: string): UseParametersReturn => {
  const [parameters, setParameters] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  const loadParams = React.useCallback(async () => {
    try {
      const data = await getParameters();
      setParameters(data[category] || []);
    } catch (error) {
      console.error("Error loading parameters:", error);
    } finally {
      setLoading(false);
    }
  }, [category]);

  React.useEffect(() => {
    loadParams();
  }, [loadParams]);

  return React.useMemo(() => ({ parameters, loading }), [parameters, loading]);
};
```

**Key Features**:

- Reactive updates when parameters change
- Loading state management
- Error handling with graceful degradation
- Memoized return values for performance
- Category-specific parameter filtering

## Data Structure

### Parameter Item Interface

```typescript
interface ParameterItem {
  id: string; // Unique identifier (UUID)
  value: any; // Parameter value (can be string, object, array)
  parent?: string; // Optional parent ID for hierarchical data
}
```

### Parameters Interface

```typescript
interface Parameters {
  [category: string]: ParameterItem[];
}
```

### Hook Return Interface

```typescript
interface UseParametersReturn {
  parameters: ParameterItem[];
  loading: boolean;
}
```

## Parameter Categories

Based on the codebase analysis, the following parameter categories are supported:

### 1. **Regio** (Regions)

- Dutch regional divisions for H-DCN organization
- Used for member regional assignments
- Examples: "Noord-Holland", "Zuid-Holland", "Friesland"

### 2. **Lidmaatschap** (Membership Types)

- Different membership categories
- Used for member classification and permissions
- Examples: "Gewoon lid", "Gezins lid", "Donateur zonder motor"

### 3. **Motormerk** (Motorcycle Brands)

- Supported motorcycle brands
- Used in member profiles and product categorization
- Examples: "Harley-Davidson", "Indian", "Buell"

### 4. **Clubblad** (Club Magazine)

- Magazine delivery preferences
- Used for member communication preferences
- Examples: "Papier", "Digitaal", "Geen"

### 5. **WieWatWaar** (How Did You Find Us)

- Member acquisition tracking
- Used for marketing analytics
- Examples: "Facebook", "Website H-DCN", "Vrienden"

### 6. **Function_permissions** (Function Permissions)

- Role-based access control configuration
- Used by FunctionPermissionManager
- Contains read/write permissions per function per role

### 7. **Productgroepen** (Product Groups)

- Hierarchical product categorization
- Used in webshop and product management
- Supports parent-child relationships

## Integration Points

### 1. **Function Permissions System**

```typescript
// From functionPermissions.ts
import { getParameters } from "./parameterService";

// Used to load function permission configuration
const parameters = await getParameters();
const functionPermissions = parameters["Function_permissions"] || [];
```

### 2. **Event Management**

```typescript
// From EventForm.tsx
import { useParameters } from "../../../utils/parameterService";

// Used for region selection in event forms
const { parameters: regions } = useParameters("Regio");
```

### 3. **Webshop Integration**

```typescript
// From CheckoutModal.tsx
import { parameterService } from "../services/api";

// Used for delivery options configuration
const response = await parameterService.getParameter("leveropties");
```

## Performance Optimizations

### 1. **Memoization**

- Conversion results are cached using `memoizedConversions` Map
- React hooks use `React.useMemo` and `React.useCallback` for optimization
- Category-specific converters prevent repeated processing

### 2. **Category-Specific Converters**

```typescript
const categoryConverters: Record<
  string,
  (items: ParameterItem[]) => ParameterItem[]
> = {
  Productgroepen: (items: ParameterItem[]) =>
    items.map((item) => {
      try {
        const parsed = JSON.parse(item.value);
        return { id: item.id, value: parsed.value, parent: parsed.parent };
      } catch {
        return item;
      }
    }),
};
```

### 3. **Flat Structure Conversion**

- Hierarchical data is converted to flat arrays for dropdown usage
- Conversion results are memoized to avoid repeated processing
- Cache key based on JSON.stringify for accurate cache hits

## Error Handling

### 1. **Service Level Errors**

- All functions wrap operations in try-catch blocks
- Dutch error messages for user-facing errors
- Detailed error logging for debugging

### 2. **React Hook Error Handling**

- Graceful degradation when parameter loading fails
- Loading states prevent UI flickering
- Empty arrays returned as fallback

### 3. **Fallback Mechanisms**

- parameterStore provides multiple fallback layers
- localStorage cache when API fails
- Default values when all else fails

## Usage Patterns

### 1. **Component Integration**

```typescript
// For dropdown/select components
const { parameters: regions, loading } = useParameters("Regio");

if (loading) return <Spinner />;

return (
  <Select>
    {regions.map((region) => (
      <option key={region.id} value={region.id}>
        {region.value}
      </option>
    ))}
  </Select>
);
```

### 2. **Administrative Operations**

```typescript
// For parameter management
const handleSave = async (category: string, value: any, id?: string) => {
  try {
    await saveParameter(category, value, id);
    await clearParameterCache(); // Refresh cache
    // Update UI
  } catch (error) {
    // Handle error
  }
};
```

### 3. **Permission System Integration**

```typescript
// For role-based access control
const parameters = await getParameters();
const functionPermissions = parameters["Function_permissions"] || [];
const permissionConfig = functionPermissions.find((p) => p.value)?.value || {};
```

## Dependencies

### 1. **parameterStore.tsx**

- Core storage and caching logic
- API integration with DynamoDB
- Fallback mechanisms

### 2. **React**

- Hooks for component integration
- State management
- Effect handling

### 3. **Crypto API**

- UUID generation for new parameters
- Browser-native crypto.randomUUID()

## Future Considerations

### 1. **Type Safety**

- Consider adding TypeScript interfaces for specific parameter categories
- Validate parameter values against expected schemas
- Add runtime type checking for critical parameters

### 2. **Real-time Updates**

- Consider WebSocket integration for real-time parameter updates
- Implement parameter change notifications
- Add optimistic updates for better UX

### 3. **Caching Strategy**

- Implement more sophisticated caching with TTL
- Add cache invalidation strategies
- Consider service worker caching for offline support

### 4. **Performance Monitoring**

- Add performance metrics for parameter loading
- Monitor cache hit rates
- Track parameter usage patterns

## Testing Considerations

### 1. **Unit Tests Needed**

- Test parameter CRUD operations
- Test error handling scenarios
- Test React hook behavior

### 2. **Integration Tests Needed**

- Test parameterStore integration
- Test API fallback scenarios
- Test cache invalidation

### 3. **Performance Tests Needed**

- Test with large parameter datasets
- Test memoization effectiveness
- Test concurrent access patterns

## Conclusion

The parameterService provides a clean, React-friendly interface for H-DCN's parameter management system. It successfully abstracts the complexity of the underlying storage mechanisms while providing robust error handling, performance optimizations, and flexible usage patterns. The service is well-integrated with the existing H-DCN architecture and provides the foundation for the upcoming Cognito authentication integration.
