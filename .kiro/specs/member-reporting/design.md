# Member Reporting Function - Design Document

## Design Overview

This document outlines the user experience design, component architecture, and data flow for the H-DCN Member Reporting Function, following the frontend-first approach and leveraging existing system patterns.

## Key Architectural Decision: Simplified Calculated Fields

**Decision**: Calculated fields are computed **only in the frontend** using the existing `frontend/src/utils/calculatedFields.ts` system.

**Benefits**:

- ✅ **Single source of truth**: No code duplication between backend and frontend
- ✅ **Guaranteed consistency**: Same calculation logic used in operational and reporting views
- ✅ **Easier maintenance**: Single place to update calculation logic
- ✅ **Proven performance**: Already tested with 1000+ members in existing components
*** Note issues for parquet generation. My Corrected Recommendation
- *** If ussing Python: Use Docker containers - it's the only practical way to get pandas + pyarrow in Lambda without major compromises.
- *** If deployment simplicity matters: Use Go - the lack of dependency complexity is a massive advantage that I understated earlier.

**Data Flow**:

```
DynamoDB (Raw Data) → Parquet (Raw Data) → Frontend (Apply calculatedFields.ts) → Reports
```

## User Experience Design

### Target Users and Use Cases

**Primary Users:**

- **Members_CRUD_All Administrators**: Full access to all reporting features including AI and central functions (ALV certificates, 10-year badges)
- **Members_Read_All Administrators**: All reporting features except AI and central functions
- **Regional Administrators**: Limited to their region's data (Members_Read_All with regional restrictions)

**Core Use Cases:**

1. **Daily Operations**: Quick member list exports for events, communications
2. **ALV Preparation**: Anniversary certificates and milestone recognition
3. **Strategic Analysis**: Regional trends, membership patterns, growth insights
4. **Administrative Tasks**: Address labels, birthday lists, financial overviews

### User Journey Flow

```
Member Admin Dashboard
    ↓
Reporting Section (New)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Quick Exports │  ALV Functions  │   Analytics     │
│                 │                 │                 │
│ • Address Labels│ • Certificates  │ • Regional Stats│
│ • Birthday Lists│ • 10-Year Badges│ • Violin Plots  │
│ • Member Lists  │ • Recognition   │ • AI Insights   │
│ • Motor Lists   │   Letters       │ • Trend Analysis│
└─────────────────┴─────────────────┴─────────────────┘
    ↓
Export Options (CSV, XLSX, PDF)
    ↓
Instant Download (Frontend Processing)
```

## Visual Design System

### Layout Structure (Following look-and-feel.md)

**Main Reporting Dashboard**

```
┌─────────────────────────────────────────────────────────────┐
│ H-DCN Portal Header (Existing)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Member Reporting Dashboard                              │
│                                                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│  │   Quick Exports │ │   Analytics     │ │ ALV Functions │ │
│  │                 │ │                 │ │(CRUD_All Only)│ │
│  │ 📄 Address      │ │ 📈 Regional     │ │ 🏆 Certificates│ │
│  │ 🎂 Birthdays    │ │ � ViolYin       │ │ �️ 10-Yr Ba dges│ │
│  │ 👥 Members      │ │ � Trendsi       │ │ 📜 Recognition │ │
│  │ 🏍️ Motors       │ │ 📋 Statistics   │ │               │ │
│  └─────────────────┘ └─────────────────┘ └───────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 💾 Data Export (Members_CRUD_All Only)                 │ │
│  │                                                         │ │
│  │ 📦 Parquet Files  📊 Export Options  🔄 Cache Status   │ │
│  │ [Generate Full]   [Filter & Export]  [Last: 2h ago]    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 🤖 AI-Powered Reporting (Members_CRUD_All Only)        │ │
│  │                                                         │ │
│  │ "Show me membership trends by region..."                │ │
│  │ [Ask AI] [Monthly Summary] [Trend Alerts]              │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Color Scheme and Components

**Following look-and-feel.md patterns:**

- **Background**: `bg="black" minH="100vh"` (dark theme)
- **Container**: `maxW="1200px" mx="auto" p={6}`
- **Section Cards**: `bg="gray.800"` with `borderColor="orange.400"`
- **Headers**: `bg="gray.700"` with `color="orange.300"`
- **Content Areas**: `bg="orange.300"` for active sections
- **Buttons**: Chakra UI icons with consistent color schemes

### Component Hierarchy

```
ReportingDashboard
├── QuickExportsSection
│   ├── ExportViewCard (Address Labels - Paper)
│   ├── ExportViewCard (Address Labels - Regional)
│   ├── ExportViewCard (Email Groups - Digital)
│   ├── ExportViewCard (Email Groups - Regional)
│   ├── ExportViewCard (Birthday Lists with Addresses)
│   ├── ExportViewCard (Member Overview)
│   └── ExportViewCard (Motor View)
├── AnalyticsSection
│   ├── RegionalStatsCard
│   ├── ViolinPlotVisualization
│   └── MembershipTrendsCard
├── ALVFunctionsSection (Members_CRUD_All only)
│   ├── YearSelector (Filter for both certificate and badge calculations)
│   ├── CertificateGenerator (Uses selected year)
│   └── BadgeRecognition (Uses selected year)
├── DataExportSection (Members_CRUD_All only)
│   ├── ParquetGenerator
│   └── DataScienceExports
└── AIReportingSection (Members_CRUD_All only)
    ├── NaturalLanguageQuery
    ├── MonthlySummaryGenerator
    └── TrendAlertSystem
```

## Data Architecture

### Simplified Hybrid Data Architecture Overview

The H-DCN Member Reporting Function implements a **simplified hybrid data architecture** that separates operational data (DynamoDB) from analytical data (Parquet) while maintaining a single source of truth for calculated fields:

**Operational Layer (DynamoDB)**

- Real-time member management and CRUD operations
- Live status updates and validations
- Immediate data consistency for day-to-day operations

**Analytics Layer (S3 Parquet)**

- **Raw member data storage** for reporting and analytics
- Optimized columnar storage for fast data loading
- Regional partitioning for access control
- **No pre-computed calculated fields** (computed on frontend)

**Calculated Fields Layer (Frontend Only)**

- **Single source of truth**: All calculated fields computed in `frontend/src/utils/calculatedFields.ts`
- **No code duplication**: Same logic used for both operational and reporting views
- **Consistent results**: Guaranteed consistency across all features
- **Easy maintenance**: Single place to update calculation logic

### Simplified Data Flow Architecture

**Complete Reporting Data Flow:**

```
DynamoDB (Operational Raw Data)
    ↓
Lambda Transform (Simple Export)
    ↓
- Export raw member data only
- No calculated field computation
- Optimize for fast parquet generation
    ↓
S3 Parquet Files (Raw Analytics Data)
    ↓
Frontend Load Raw Parquet Data
    ↓
Frontend Compute Calculated Fields (calculatedFields.ts)
    ↓
Frontend-First Processing (xlsx, jsPDF, @visx/stats)
    ↓
Reports, Exports, Visualizations
```

**Key Principle: "Frontend-First Processing with Single Source of Truth"**

- **Data Source**: Parquet files from S3 contain raw DynamoDB data
- **Calculated Fields**: Computed only in frontend using existing `calculatedFields.ts`
- **Processing Location**: Frontend handles all report generation, filtering, and visualization
- **Consistency**: Single implementation guarantees identical results everywhere
- **Performance**: Raw parquet loading + frontend calculation is fast enough for 1,500 members

**Simplified AI Processing Flow:**

```
S3 Parquet Data (Raw)
    ↓
Frontend Load and Compute Calculated Fields
    ↓
Aggregated Data Summary (Frontend)
    ↓
Backend AI Proxy (OpenRouter.ai)
    ↓
AI Response
    ↓
Frontend Display
```

### Data Sources Integration

**Primary Data Source: S3 Parquet Files (Raw Data)**

1. **Parquet Member Data**: Raw member data from DynamoDB stored in S3
2. **Calculated Fields**: Computed in frontend using `frontend/src/utils/calculatedFields.ts`
3. **Table Contexts**: Applied as filters on loaded and processed parquet data
4. **Permissions**: Regional filtering applied during parquet data loading

**Supporting Data Sources:**

- **Export Preferences**: User settings for default formats (localStorage)
- **AI Query History**: Recent queries and responses (session storage)
- **Report Templates**: Predefined report configurations (static config)

**Critical Implementation Note:**

- **All reporting features load raw data from Parquet files, NOT from existing DynamoDB member tables**
- **The existing member table data is for operational CRUD, not reporting**
- **Parquet files contain raw data; calculated fields are computed in frontend**
- **Single source of truth for calculated fields eliminates code duplication**

### Implementation Dependencies

**Critical Implementation Order:**

1. **Backend Parquet Generation** (Phase 1.1) - **MUST BE IMPLEMENTED FIRST**

   - Lambda function to export raw DynamoDB data → Parquet
   - **No calculated field computation in backend**
   - Store in S3 with proper permissions

2. **Frontend Parquet Loading Service** (Phase 2.1)

   - Service to load raw Parquet data from S3
   - **Apply calculated fields using existing `calculatedFields.ts`**
   - Handle regional filtering and permissions
   - Cache processed data for performance

3. **Frontend Reporting Components** (Phases 2-6)
   - All reporting features use processed Parquet data as source
   - Process loaded and calculated Parquet data for exports and visualizations
   - No direct DynamoDB queries for reporting

**Why This Order Matters:**

- Frontend reporting components need processed parquet data to function properly
- Building frontend first without parquet backend creates technical debt
- Raw parquet files provide the data foundation; frontend adds the intelligence
- Single calculated field implementation eliminates maintenance overhead

**Data Loading Pattern for All Components:**

```typescript
// All reporting components follow this pattern:
const ReportingComponent: React.FC = () => {
  const [memberData, setMemberData] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadReportingData = async () => {
      // 1. Load raw data from Parquet
      const rawData = await ParquetDataService.loadRawMemberData();

      // 2. Apply calculated fields using existing frontend logic
      const processedData = computeCalculatedFieldsForArray(rawData);

      // 3. Apply regional filtering
      const filteredData = applyRegionalFiltering(processedData);

      setMemberData(filteredData);
      setLoading(false);
    };

    loadReportingData();
  }, []);

  // Process memberData for reports, exports, visualizations
};
```

### 1. ExportViewCard Component

**Purpose**: Represents each export view with format options

**Specific Export Views:**

**Address Stickers (Paper Clubblad)**

```
┌─────────────────────────────────┐
│ 📄 Address Stickers (Paper)     │
│ Voor papieren clubblad verzending│
│                                 │
│ Filter: Clubblad = "Papier"     │
│ Fields: korte_naam, address     │
│                                 │
│ [CSV] [XLSX] [PDF] [Preview]    │
│                                 │
│ 👥 234 members • Updated 5m     │
└─────────────────────────────────┘
```

**Address Stickers (Regional)**

```
┌─────────────────────────────────┐
│ 📄 Address Stickers (Regional)  │
│ Voor regionale mailings         │
│                                 │
│ Filter: By user's region        │
│ Fields: korte_naam, address     │
│                                 │
│ [CSV] [XLSX] [PDF] [Preview]    │
│                                 │
│ 👥 156 members • Updated 5m     │
└─────────────────────────────────┘
```

**Email Groups (Digital Clubblad)**

```
┌─────────────────────────────────┐
│ 📧 Email List (Digital)         │
│ Voor digitale clubblad verzending│
│                                 │
│ Filter: Clubblad = "Digitaal"   │
│ Fields: korte_naam, email       │
│                                 │
│ [CSV] [XLSX] [TXT] [Preview]    │
│                                 │
│ 👥 987 members • Updated 5m     │
└─────────────────────────────────┘
```

**Email Groups (Regional)**

```
┌─────────────────────────────────┐
│ 📧 Email List (Regional)        │
│ Voor regionale communicatie     │
│                                 │
│ Filter: By user's region        │
│ Fields: korte_naam, email       │
│                                 │
│ [CSV] [XLSX] [TXT] [Preview]    │
│                                 │
│ 👥 156 members • Updated 5m     │
└─────────────────────────────────┘
```

**Birthday Lists with Addresses**

```
┌─────────────────────────────────┐
│ 🎂 Birthday List with Addresses │
│ Voor verjaardagskaarten/cadeaus │
│                                 │
│ Filter: Status = "Actief"       │
│ Fields: korte_naam, verjaardag, │
│         address, email, telefoon│
│                                 │
│ [CSV] [XLSX] [PDF] [Preview]    │
│                                 │
│ 👥 1,234 members • Updated 5m   │
└─────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ExportViewCardProps {
  viewName: string;
  context: TableContextConfig;
  memberCount: number;
  onExport: (format: "csv" | "xlsx" | "pdf" | "txt") => void;
  onPreview: () => void;
}
```

### ALVFunctionsSection Component

**Purpose**: Year-based certificate and badge generation with shared year filter (Members_CRUD_All only - central functions)

**Visual Design:**

```
┌─────────────────────────────────────────────────────────┐
│ 🏆 ALV Functions (Members_CRUD_All Only)               │
│                                                         │
│ Year: [2024 ▼] (Current year minus 3 to plus 3)        │
│                                                         │
│ ┌─────────────────────┐ ┌─────────────────────────────┐ │
│ │ 🏆 ALV Certificates │ │ 🎖️ 10-Year Badges          │ │
│ │                     │ │                             │ │
│ │ Preview:            │ │ Eligible Members:           │ │
│ │ • 25 jaar: 12 mbrs  │ │ • 15 members qualify        │ │
│ │ • 30 jaar: 8 mbrs   │ │   for 10-year badge         │ │
│ │ • 35 jaar: 5 mbrs   │ │                             │ │
│ │                     │ │ [Generate PDF and/or List]  │ │
│ │ [Generate PDF and/or List] │ │                      │ │
│ └─────────────────────┘ └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**State Management:**

```typescript
interface ALVFunctionsState {
  selectedYear: number;
  certificateEligible: Record<string, Member[]>; // Grouped by milestone
  badgeEligible: Member[]; // 10-year badge eligible
  isCalculating: boolean;
}

// Year selector affects both certificate and badge calculations
const handleYearChange = (year: number) => {
  setSelectedYear(year);
  // Recalculate both certificates and badges for the new year
  calculateCertificateEligibility(year);
  calculateBadgeEligibility(year);
};
```

**Calculation Logic:**

```typescript
// Both functions use the same year parameter from the shared selector
const calculateCertificateEligibility = (year: number) => {
  const cutoffDate = new Date(`${year}-04-01`); // ALV date
  // Calculate years of membership using tijdstempel field
  // Group by milestones (25, 30, 35, 40, 45, 50+)
};

const calculateBadgeEligibility = (year: number) => {
  const cutoffDate = new Date(`${year}-04-01`); // ALV date
  // Find members with exactly 10 years of membership
};
```

### 3. ParquetGenerator Component (Members_CRUD_All Only)

**Purpose**: Generate Parquet files for data science and advanced analytics workflows

**Visual Design:**

```
┌─────────────────────────────────────────────────────────┐
│ 💾 Data Export (Members_CRUD_All Only)                 │
│                                                         │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐ │
│ │ 📦 Full Dataset │ │ 📊 Export       │ │ 🔄 Status   │ │
│ │                 │ │    Options      │ │             │ │
│ │ All members     │ │ □ Include PII   │ │ Last: 2h ago│ │
│ │ with calculated │ │ □ Anonymize     │ │ Size: 2.3MB │ │
│ │ fields          │ │ □ Active only   │ │ Records: 1.5K│ │
│ │                 │ │ □ With motors   │ │             │ │
│ │ [Generate New]  │ │ [Apply Filters] │ │ [Refresh]   │ │
│ └─────────────────┘ └─────────────────┘ └─────────────┘ │
│                                                         │
│ Progress: [████████████████████████████████] 100%      │
│ Status: Ready for download • Generated: 2h ago         │
│ [Download Parquet File]                                │
└─────────────────────────────────────────────────────────┘
```

**State Management:**

```typescript
interface ParquetGeneratorState {
  isGenerating: boolean;
  progress: number;
  lastGenerated: Date | null;
  fileSize: string;
  recordCount: number;
  error: string | null;
}

interface ParquetGenerationOptions {
  includeCalculatedFields: boolean;
  includePII: boolean; // Include personal identifiable information
  anonymize: boolean; // Anonymize sensitive data for external analysis
  activeOnly: boolean; // Only include active members
  withMotors: boolean; // Only include members with motor information
  dateRange?: {
    from: Date;
    to: Date;
  };
}
```

**Backend Integration:**

```typescript
const generateParquetFile = async (options: ParquetGenerationOptions) => {
  // Call backend Lambda function
  const response = await fetch("/api/generate-parquet", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      options,
      timestamp: new Date().toISOString(),
    }),
  });

  if (!response.ok) {
    throw new Error("Parquet generation failed");
  }

  // Backend returns the file content directly or a temporary signed URL
  return await response.json();
};

const downloadParquetFile = async () => {
  // Always go through backend API - no direct S3 links
  const response = await fetch("/api/download-parquet", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!response.ok) {
    throw new Error("Download failed");
  }

  // Trigger browser download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `hdcn-members-${new Date().toISOString().split("T")[0]}.parquet`;
  a.click();
  window.URL.revokeObjectURL(url);
};
```

**Features:**

- **Single Dataset Export**: Complete member database with all calculated fields (no partitioning needed for 1500 records)
- **Flexible Filtering**: Options to include/exclude PII, anonymize data, filter by status or motor ownership
- **Progress Tracking**: Real-time progress updates during generation
- **Cache Status**: Shows last generation time and file metadata
- **API-based Download**: Files served through backend API (no direct S3 links that could break)
- **Data Privacy Options**: Configurable anonymization for external analysis

### 4. ViolinPlotVisualization Component

**Purpose**: Regional analytics with interactive violin plots

**Visual Design:**

```
┌─────────────────────────────────┐
│ 📈 Regional Analytics           │
│                                 │
│ Metric: [Age ▼] [Membership ▼]  │
│                                 │
│     🎻 Violin Plot Area         │
│   ┌─────────────────────────┐   │
│   │    Interactive Plot     │   │
│   │   (Age by Region)       │   │
│   └─────────────────────────┘   │
│                                 │
│ [Export Chart] [Full Screen]    │
└─────────────────────────────────┘
```

**Data Processing:**

```typescript
interface ViolinPlotData {
  metric: "leeftijd" | "jaren_lid";
  data: Array<{
    regio: string;
    value: number;
    member_id: string;
  }>;
}
```

### 5. AIReportingInterface Component (Members_CRUD_All Only)

**Purpose**: Natural language queries and AI insights

**Visual Design:**

```
┌─────────────────────────────────┐
│ 🤖 AI-Powered Reporting         │
│ (Members_CRUD_All Only)         │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Ask about membership data...│ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Ask AI] [Monthly Summary]      │
│ [Trend Alerts] [Clear History]  │
│                                 │
│ Recent Insights:                │
│ • "Membership growth in Noord"  │
│ • "Age distribution analysis"   │
└─────────────────────────────────┘
```

**Interaction Flow:**

1. User types natural language query
2. Frontend prepares anonymized data summary
3. Backend proxy calls OpenRouter.ai
4. Response displayed with context
5. Query saved to session history

## Technical Architecture

### Frontend Components Structure

```
src/modules/reporting/
├── components/
│   ├── ReportingDashboard.tsx
│   ├── ExportViewCard.tsx
│   ├── CertificateGenerator.tsx
│   ├── BadgeRecognition.tsx
│   ├── ViolinPlotVisualization.tsx
│   ├── AIReportingInterface.tsx
│   └── ReportPreviewModal.tsx
├── services/
│   ├── MemberExportService.ts
│   ├── CertificateService.ts
│   ├── AnalyticsService.ts
│   └── AIReportingService.ts
├── hooks/
│   ├── useReportingData.ts
│   ├── useExportFormats.ts
│   └── useAIReporting.ts
└── types/
    ├── ReportingTypes.ts
    └── ExportTypes.ts
```

### Service Layer Design

**MemberExportService**

```typescript
class MemberExportService {
  // Process raw parquet data with calculated fields before export
  exportToCSV(viewName: string, rawMembers: Member[]): void {
    // 1. Apply calculated fields using existing calculatedFields.ts
    const processedMembers = computeCalculatedFieldsForArray(rawMembers);
    // 2. Apply view-specific filtering and column selection
    // 3. Generate CSV export
  }

  exportToXLSX(viewName: string, rawMembers: Member[]): void;
  exportToPDF(viewName: string, rawMembers: Member[]): void;
  exportToTXT(viewName: string, rawMembers: Member[]): void; // For email lists
  previewExport(viewName: string, rawMembers: Member[]): ExportPreview;

  // Specific export functions
  exportAddressStickers(filter: "paper" | "regional", format: string): void;
  exportEmailGroups(filter: "digital" | "regional", format: string): void;
}
```

**Export View Configurations:**

```typescript
// Add to memberFields.ts or separate reporting config
export const REPORTING_EXPORT_VIEWS = {
  addressStickersPaper: {
    name: "Address Stickers (Paper)",
    description: "Address labels for paper clubblad distribution",
    filter: { clubblad: "Papier", status: "Actief" },
    columns: [
      { fieldKey: "korte_naam", visible: true, order: 1 },
      { fieldKey: "straat", visible: true, order: 2 },
      { fieldKey: "postcode", visible: true, order: 3 },
      { fieldKey: "woonplaats", visible: true, order: 4 },
      { fieldKey: "land", visible: true, order: 5 },
    ],
    formats: ["csv", "xlsx", "pdf"],
    permissions: { view: ["Members_Read_All", "Members_CRUD_All"] },
  },

  addressStickersRegional: {
    name: "Address Stickers (Regional)",
    description: "Address labels for regional mailings",
    filter: { status: "Actief" }, // Regional filter applied automatically
    columns: [
      { fieldKey: "korte_naam", visible: true, order: 1 },
      { fieldKey: "straat", visible: true, order: 2 },
      { fieldKey: "postcode", visible: true, order: 3 },
      { fieldKey: "woonplaats", visible: true, order: 4 },
      { fieldKey: "land", visible: true, order: 5 },
    ],
    formats: ["csv", "xlsx", "pdf"],
    regionalRestricted: true,
    permissions: { view: ["Members_Read_All", "Members_CRUD_All"] },
  },

  emailGroupsDigital: {
    name: "Email Groups (Digital)",
    description: "Email addresses for digital clubblad distribution",
    filter: { clubblad: "Digitaal", status: "Actief" },
    columns: [
      { fieldKey: "korte_naam", visible: true, order: 1 },
      { fieldKey: "email", visible: true, order: 2 },
    ],
    formats: ["csv", "xlsx", "txt"],
    permissions: {
      view: ["Members_Read_All", "Members_CRUD_All", "Communication_Read_All"],
    },
  },

  emailGroupsRegional: {
    name: "Email Groups (Regional)",
    description: "Email addresses for regional communication",
    filter: { status: "Actief" }, // Regional filter applied automatically
    columns: [
      { fieldKey: "korte_naam", visible: true, order: 1 },
      { fieldKey: "email", visible: true, order: 2 },
    ],
    formats: ["csv", "xlsx", "txt"],
    regionalRestricted: true,
    permissions: {
      view: ["Members_Read_All", "Members_CRUD_All", "Communication_Read_All"],
    },
  },

  birthdayList: {
    name: "Birthday List with Addresses",
    description: "Member birthdays with full addresses for cards/gifts",
    filter: { status: "Actief" },
    columns: [
      { fieldKey: "korte_naam", visible: true, order: 1 },
      { fieldKey: "verjaardag", visible: true, order: 2 }, // Uses calculated field
      { fieldKey: "straat", visible: true, order: 3 },
      { fieldKey: "postcode", visible: true, order: 4 },
      { fieldKey: "woonplaats", visible: true, order: 5 },
      { fieldKey: "land", visible: true, order: 6 },
      { fieldKey: "email", visible: true, order: 7 },
      { fieldKey: "telefoon", visible: true, order: 8 },
    ],
    formats: ["csv", "xlsx", "pdf"],
    permissions: { view: ["Members_Read_All", "Members_CRUD_All"] },
  },

  // Existing table contexts from memberFields.ts can also be used as export views
  memberOverview: MEMBER_TABLE_CONTEXTS.memberOverview,
  motorView: MEMBER_TABLE_CONTEXTS.motorView,
  communicationView: MEMBER_TABLE_CONTEXTS.communicationView,
  financialView: MEMBER_TABLE_CONTEXTS.financialView,
};
```

**CertificateService**

```typescript
class CertificateService {
  // Use calculated jaren_lid field computed from raw parquet data
  generateALVCertificates(year: number, rawMembers: Member[]): void {
    // 1. Apply calculated fields to get jaren_lid
    const processedMembers = computeCalculatedFieldsForArray(rawMembers);
    // 2. Filter and group by certificate milestones
    // 3. Generate certificates
  }

  generate10YearBadges(year: number, rawMembers: Member[]): void;
  previewCertificates(year: number, rawMembers: Member[]): CertificatePreview;
}
```

**AnalyticsService**

```typescript
class AnalyticsService {
  // Process raw parquet data with calculated fields for analytics
  getRegionalStats(rawMembers: Member[]): RegionalStats {
    // 1. Apply calculated fields using existing calculatedFields.ts
    const processedMembers = computeCalculatedFieldsForArray(rawMembers);
    // 2. Generate regional statistics
  }

  getAgeDistribution(rawMembers: Member[]): ViolinPlotData {
    // 1. Compute leeftijd field from raw data
    const processedMembers = computeCalculatedFieldsForArray(rawMembers);
    // 2. Generate age distribution data
  }

  getMembershipDurationStats(rawMembers: Member[]): ViolinPlotData {
    // 1. Compute jaren_lid field from raw data
    const processedMembers = computeCalculatedFieldsForArray(rawMembers);
    // 2. Generate membership duration statistics
  }
}
```

## Integration Points

### With Existing Systems

**memberFields.ts Integration:**

- Reuse calculated field definitions
- Leverage table context configurations
- Maintain consistent field labeling
- Apply existing permission structures

**look-and-feel.md Compliance:**

- Dark theme with orange accents
- Consistent card patterns
- Chakra UI icon standards
- Responsive grid layouts

**guardrail.md Security:**

- Members_CRUD_All permission checks
- No dangerous data exposure
- Secure AI API proxy
- Audit logging for sensitive operations

### Navigation Integration

**Option B: Tab-based Integration (Selected Approach)**

Add "Rapportages" as a new tab within the existing Ledenadministratie section:

```typescript
// Add as tabs within the existing Members section
const MemberAdminTabs = [
  {
    label: "Overzicht",
    path: "/members/overview",
    icon: <ViewIcon />,
    requiredRoles: [
      "Members_Read_All",
      "Members_CRUD_All",
      "System_User_Management",
    ],
  },
  {
    label: "Rapportages",
    path: "/members/reporting",
    icon: <DownloadIcon />,
    requiredRoles: [
      "Members_Read_All",
      "Members_CRUD_All",
      "System_User_Management",
    ], // Not extra restrictive than overview
  },
];
```

**Tab Navigation Component:**

```typescript
const MemberAdminNavigation: React.FC = () => {
  const location = useLocation();
  const { hasRole } = useAuth();

  // Check if user has any reporting access
  const hasReportingAccess =
    hasRole("Members_CRUD_All") ||
    hasRole("Members_Read_All") ||
    hasRole("System_User_Management");

  return (
    <Tabs index={getActiveTabIndex(location.pathname)}>
      <TabList bg="gray.700" borderColor="orange.400">
        <Tab
          color="white"
          _selected={{ color: "orange.300", borderColor: "orange.400" }}
        >
          <HStack spacing={2}>
            <ViewIcon />
            <Text>Overzicht</Text>
          </HStack>
        </Tab>

        {hasReportingAccess && (
          <Tab
            color="white"
            _selected={{ color: "orange.300", borderColor: "orange.400" }}
          >
            <HStack spacing={2}>
              <DownloadIcon />
              <Text>Rapportages</Text>
            </HStack>
          </Tab>
        )}
      </TabList>

      <TabPanels>
        <TabPanel p={0}>
          <MemberOverviewPage />
        </TabPanel>

        {hasReportingAccess && (
          <TabPanel p={0}>
            <MemberReportingDashboard />
          </TabPanel>
        )}
      </TabPanels>
    </Tabs>
  );
};
```

**Permission-Based Feature Access:**

```typescript
// Inside MemberReportingDashboard component
const MemberReportingDashboard: React.FC = () => {
  const { hasRole } = useAuth();

  return (
    <VStack spacing={6}>
      {/* Quick Exports - Available to all reporting users */}
      <QuickExportsSection />

      {/* Analytics - Available to all reporting users */}
      <AnalyticsSection />

      {/* ALV Functions - Members_CRUD_All only (central function) */}
      {hasRole("Members_CRUD_All") && <ALVFunctionsSection />}

      {/* Data Export (Parquet) - Members_CRUD_All only */}
      {hasRole("Members_CRUD_All") && <DataExportSection />}

      {/* AI Reporting - Members_CRUD_All only */}
      {hasRole("Members_CRUD_All") && <AIReportingSection />}
    </VStack>
  );
};
```

**URL Structure:**

- `/members/overview` - Member table and management (existing)
- `/members/reporting` - New reporting dashboard

**Breadcrumb Navigation:**

```
H-DCN Portal > Ledenadministratie > Rapportages
```

**User Experience Benefits:**

- **Familiar pattern**: Uses existing tab structure users already know
- **Contextual access**: Reporting stays within member administration context
- **Permission-based visibility**: Only Members_CRUD_All users see the Rapportages tab
- **Seamless switching**: Easy to switch between member overview and reporting
- **Clean integration**: No menu restructuring needed
- What would feel most natural for H-DCN administrators?
  },
  ];

```

**Breadcrumb Navigation:**

```

H-DCN Portal > Ledenadministratie > Rapportages > ALV Functies

```

**User Experience Benefits:**

- **Logical grouping**: Reporting stays within member administration context
- **Familiar navigation**: Users already know where to find member functions
- **Permission inheritance**: Builds on existing member administration permissions
- **Reduced menu clutter**: Avoids creating another top-level menu item

## Performance Considerations

### Frontend Optimization

**Data Processing:**

- Use React.useMemo for expensive calculations
- Implement virtual scrolling for large datasets
- Lazy load visualization components
- Cache processed data in session storage

**Export Performance:**

- Stream large exports to prevent memory issues
- Show progress indicators for PDF generation
- Implement cancellation for long-running operations
- Use Web Workers for heavy processing

**Bundle Size:**

- Code split reporting modules
- Lazy load PDF/Excel libraries
- Tree shake unused visualization components
- Optimize chart rendering libraries

## Accessibility Design

### WCAG Compliance

**Visual Design:**

- High contrast colors (orange on dark backgrounds)
- Minimum 44px touch targets for mobile
- Clear focus indicators for keyboard navigation
- Semantic HTML structure with proper headings

**Screen Reader Support:**

- ARIA labels for all interactive elements
- Status announcements for export completion
- Descriptive text for chart visualizations
- Keyboard shortcuts for common actions

**Mobile Optimization:**

- Responsive card layouts
- Touch-friendly export buttons
- Simplified mobile interface
- Offline capability for loaded data

## Error Handling Design

### User-Friendly Error States

**Export Failures:**

- Clear error messages with retry options
- Fallback to alternative formats
- Progress indicators with cancellation
- Helpful troubleshooting tips

**AI Service Errors:**

- Graceful degradation when AI unavailable
- Clear indication of service status
- Alternative manual reporting options
- Retry mechanisms with backoff

**Data Processing Errors:**

- Validation of member data before processing
- Clear indication of data quality issues
- Options to exclude problematic records
- Detailed error logs for administrators

## Success Metrics

### User Experience Metrics

- **Time to Export**: < 5 seconds for standard exports
- **User Adoption**: % of Members_CRUD_All users using reporting features
- **Error Rate**: < 2% for all export operations
- **User Satisfaction**: Feedback scores and usage patterns

### Technical Performance

- **Bundle Size**: < 500KB additional for reporting modules
- **Memory Usage**: < 100MB for large dataset processing
- **Export Speed**: 1000 members/second for CSV, 500/second for PDF
- **AI Response Time**: < 10 seconds for standard queries

## Next Steps

1. **Review and Approve Design** - Stakeholder feedback on UX and technical approach
2. **Create Detailed Tasks** - Break down into implementable user stories
3. **Set Up Development Environment** - Install required libraries and tools
4. **Build MVP Components** - Start with basic export functionality
5. **Iterate Based on Feedback** - Refine UX and add advanced features

This design provides a solid foundation for building a user-friendly, performant, and maintainable reporting system that leverages H-DCN's existing architecture while providing powerful new capabilities.
```
