# Requirements Document

## Introduction

The Member Reporting Function provides comprehensive data access and analysis capabilities for the H-DCN member database. This system enables day-to-day operational tasks and strategic analysis through various export formats, automated certificate generation, and advanced visualization tools.

## Glossary

- **System**: The H-DCN Member Reporting Function
- **Member_Table**: The central database table containing all member information
- **Regio**: Regional division within H-DCN organization
- **ALV**: Algemene Leden Vergadering (General Members Meeting)
- **Lidmaatschap**: Membership type (Gewoon lid, Gezins lid, Donateur, Gezins donateur)
- **Ingangsdatum**: Member start date (mapped to tijdstempel field)
- **Violin_Plot**: Statistical visualization showing data distribution
- **Export_View**: Predefined data selection for export purposes
- **AI_Agent**: OpenRouter.ai powered reporting assistant

## System Architecture

The H-DCN Member Reporting Function implements a hybrid data architecture optimizing both real-time operations and analytics performance:

### Data Storage Strategy

**Real-time Layer (DynamoDB)**

- Live member management and CRUD operations
- Real-time status updates and validations
- Immediate data consistency requirements

**Analytics Layer (Parquet)**

- Reporting and analytics workloads using raw member data (calculated fields computed in frontend)
- Data exports and visualizations
- AI/ML processing workflows with OpenRouter.ai integration
- Columnar storage for optimized query performance

**Data Flow Architecture**

```
DynamoDB (Raw Data) → Lambda (Export Raw Data) → S3 Parquet (Raw Analytics Data) → Frontend (Compute Calculated Fields) → Reporting Tools
```

The system generates Parquet files on-demand by Members_CRUD_All users, with regional partitioning for access control and lifecycle management for cost optimization. Calculated fields are computed in the frontend using the existing `calculatedFields.ts` system to ensure consistency and eliminate code duplication.

## Requirements

### Requirement 1: Data Export Functionality

**User Story:** As a H-DCN administrator, I want to export member data in various formats, so that I can use the information for operational tasks and external communications.

#### Acceptance Criteria

1. WHEN an administrator selects an export view, THE System SHALL provide export options in CSV, XLSX, and PDF formats
2. WHEN exporting address data, THE System SHALL include korte_naam, straat, postcode, woonplaats, and land fields
3. WHEN exporting birthday data, THE System SHALL include korte_naam and verjaardag (formatted as "september 26") fields
4. WHEN filtering for paper clubblad distribution, THE System SHALL only include members WHERE clubblad equals "Papier"
5. WHEN creating email distribution lists, THE System SHALL only include members WHERE clubblad equals "Digitaal" AND email is not empty
6. WHEN applying regional filters, THE System SHALL restrict data to the user's assigned regio for regional administrators
7. THE System SHALL support all existing table views for export functionality

### Requirement 2: ALV Certificate Generation

**User Story:** As a H-DCN administrator, I want to generate anniversary certificates for long-term members, so that I can recognize their loyalty during the Annual General Meeting.

#### Acceptance Criteria

1. WHEN calculating membership years, THE System SHALL use the formula Years(YYYY-04-01 - ingangsdatum)
2. WHEN displaying certificate candidates, THE System SHALL show members with 25, 30, 35, 40, 45, 50+ years of membership
3. WHEN selecting a year, THE System SHALL provide options from current year minus 3 to current year plus 3
4. WHEN generating certificates, THE System SHALL create printable documents with member names and years of service
5. THE System SHALL allow batch processing of multiple certificates
6. THE System SHALL include H-DCN branding and graphics in certificate templates

### Requirement 3: 10-Year Badge Recognition

**User Story:** As a H-DCN administrator, I want to identify members eligible for 10-year badges, so that I can recognize their continued membership.

#### Acceptance Criteria

1. WHEN calculating badge eligibility, THE System SHALL use the formula Years(YYYY-04-01 - ingangsdatum)
2. WHEN displaying eligible members, THE System SHALL show members with exactly 10 years of membership
3. WHEN generating recognition letters, THE System SHALL create printable documents with member details
4. THE System SHALL include H-DCN branding and graphics in letter templates

### Requirement 4: Regional Membership Analytics

**User Story:** As a H-DCN regional coordinator, I want to view membership statistics for my region, so that I can understand membership composition and trends.

#### Acceptance Criteria

1. WHEN displaying regional statistics, THE System SHALL only include members WHERE status equals "Actief"
2. WHEN counting members by type, THE System SHALL include "Gewoon lid", "Gezins lid", "Donateur", and "Gezins donateur"
3. WHEN showing dashboard view, THE System SHALL display member counts per regio per lidmaatschap type
4. WHEN displaying regional logos, THE System SHALL retrieve logo images from S3 storage
5. WHEN creating age distribution charts, THE System SHALL use violin plots powered by @visx/stats
6. WHEN creating membership duration charts, THE System SHALL use violin plots showing jaren_lid distribution
7. THE System SHALL update visualizations in real-time when filters are applied

### Requirement 5: AI-Powered Reporting

**User Story:** As a H-DCN administrator with Members_CRUD_All permissions, I want to generate custom reports using AI assistance, so that I can create insights and presentations efficiently.

#### Acceptance Criteria

1. WHEN accessing AI reporting features, THE System SHALL restrict access to users with Members_CRUD_All role only
2. WHEN using AI reporting, THE System SHALL connect to OpenRouter.ai API
3. WHEN generating reports, THE System SHALL use existing export views as source data
4. WHEN creating visualizations, THE System SHALL generate presentation-quality graphs and tables
5. WHEN providing download options, THE System SHALL support CSV, XLSX, PowerPoint, and HTML formats
6. WHEN using prompts, THE System SHALL provide a curated set of reporting templates
7. WHEN customizing prompts, THE System SHALL allow users to enhance predefined templates
8. THE System SHALL maintain data privacy and security when using external AI services
9. WHEN implementing AI features, THE System SHALL follow the phased "Start Small" approach outlined in [aiConsiderations.md](./aiConsiderations.md)
10. WHEN generating AI content, THE System SHALL require human validation for all strategic insights and recommendations

### Requirement 6: Calculated Field Integration

**User Story:** As a system user, I want calculated fields to be automatically available in reports, so that I don't need to manually compute derived values.

#### Acceptance Criteria

1. WHEN using korte_naam field, THE System SHALL automatically concatenate voornaam + tussenvoegsel + achternaam using frontend calculation logic
2. WHEN using leeftijd field, THE System SHALL automatically calculate age from geboortedatum using frontend calculation logic
3. WHEN using verjaardag field, THE System SHALL automatically extract day and month in Dutch format using frontend calculation logic
4. WHEN using jaren_lid field, THE System SHALL automatically calculate years since ingangsdatum using frontend calculation logic
5. WHEN using aanmeldingsjaar field, THE System SHALL automatically extract year from ingangsdatum using frontend calculation logic
6. THE System SHALL update calculated fields in real-time when source data changes
7. THE System SHALL use the existing `frontend/src/utils/calculatedFields.ts` implementation to ensure consistency across operational and reporting views

### Requirement 7: Security and Access Control

**User Story:** As a H-DCN administrator, I want to control access to sensitive member data, so that privacy and organizational policies are maintained.

#### Acceptance Criteria

1. WHEN accessing regional data, THE System SHALL restrict regional administrators to their assigned regio
2. WHEN exporting personal data, THE System SHALL log all export activities for audit purposes
3. WHEN using AI services, THE System SHALL anonymize sensitive personal information
4. THE System SHALL require appropriate user roles for different reporting functions
5. THE System SHALL comply with GDPR requirements for data processing and export

### Requirement 8: Performance and Scalability

**User Story:** As a system user, I want reports to generate quickly, so that I can work efficiently with large datasets.

#### Acceptance Criteria

1. WHEN exporting data, THE System SHALL complete exports of up to 2000 members within 30 seconds
2. WHEN generating visualizations, THE System SHALL render violin plots within 5 seconds
3. WHEN applying filters, THE System SHALL update results within 2 seconds
4. THE System SHALL support concurrent report generation by multiple users
5. THE System SHALL cache frequently accessed data to improve performance

### Requirement 9: Data Storage and Caching Strategy

**User Story:** As a system administrator, I want efficient data storage for reporting, so that analytics queries perform optimally and costs are minimized.

#### Acceptance Criteria

1. WHEN generating reports, THE System SHALL create Parquet files on-demand for analytical workloads
2. WHEN Members_CRUD_All users request data exports, THE System SHALL generate optimized Parquet files with raw member data
3. WHEN storing analytical data, THE System SHALL use columnar Parquet format for improved query performance
4. WHEN caching report data, THE System SHALL store Parquet files in S3 with appropriate lifecycle policies
5. WHEN data changes occur, THE System SHALL invalidate and regenerate relevant Parquet cache files
6. THE System SHALL support both real-time DynamoDB queries and cached Parquet analytics workflows
7. THE System SHALL compute calculated fields (korte_naam, leeftijd, verjaardag, jaren_lid, aanmeldingsjaar) in the frontend using existing calculation logic
