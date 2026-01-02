What would be the best way to define which fields should be used and shown in the member administration view mode and edit mode and the the Lidmaatschap (new applicants) and existing members I(what shown readonly and what shown and can be edited)

5. Hybrid Approach (Recommended)
   Combine a base field registry with context-specific overrides:

Base registry defines all possible fields
Context configs reference base fields with overrides
Role-based rules applied on top
This gives you flexibility while maintaining consistency and avoiding duplication.

Which approach resonates most with your team's technical comfort level and maintenance preferences?

The base field registry would store comprehensive metadata for each field. Here's what information would typically be included:

Core Field Properties
Field key (e.g., voornaam, geboortedatum)
Display label (Dutch: "Voornaam", "Geboortedatum")
Data type (string, date, number, boolean, enum)
Input type (text, email, date, select, textarea, number)
Validation Rules
Required (boolean or conditional logic)
Format validation (email, phone, postal code patterns)
Min/max length or value ranges
Custom validation rules
UI Rendering
Field group/section (Personal, Address, Membership, Motor, Financial)
Display order within group
Placeholder text
Help text/tooltips
Input size/width hints
Business Logic
Conditional visibility (show field X only if field Y has value Z)
Dependent fields (changing this field affects others)
Default values or calculation rules
Membership type relevance (motor fields only for certain membership types)
Permission Context
Sensitivity level (public, member-only, admin-only, financial)
Edit restrictions (who can modify this field)
View restrictions (who can see this field)
Self-service allowed (can members edit their own data)
Data Source
Backend field mapping (handles field name variations)
Legacy field aliases (for backward compatibility)
Data transformation rules (date format conversion, etc.)
This creates a single source of truth that all contexts (view, edit, forms) can reference and customize as needed.

Stop here the following is not intended for now

Update the guardrail or add a development guiradrail to state tough does and donts during this development phase.
Selecting productsubgroep werk niet

- Laat alleen productgroepen zien en niet de geneste structuur
  -Het selectie nmechanisme is veel te groot ten opzichte van het hele scherm

## Member Field Configuration - created_at Field Cleanup

### Completed:

- ✅ **Field registry updated** - `created_at` in plaats van `tijdstempel`

### Todo:

- 🔄 **Check DynamoDB mapping** - zorgen dat `created_at` correct wordt gelezen uit database
- 🔄 **Fix member detail modal** - "Lid sinds" moet `ingangsdatum` gebruiken (niet `created_at`/`tijdstempel`)
- 🔄 **Add backend alias** - `tijdstempel` als alias voor `created_at` indien nodig voor backward compatibility
- 🔄 **Update member table** - controleren dat "Lid sinds" kolom `ingangsdatum` gebruikt (niet `created_at`)

### Context:

Het `tijdstempel` veld was verwarrend omdat het de database record aanmaak datum bevatte, niet de werkelijke lidmaatschap start datum. Nu is het hernoemd naar `created_at` voor technische duidelijkheid. De werkelijke "Lid sinds" datum moet `ingangsdatum` gebruiken.
