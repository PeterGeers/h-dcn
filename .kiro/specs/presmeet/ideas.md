⚠️ Issues Found
1. Regio_Pressmeet not in HDCNGroup type definition

The TypeScript type HDCNGroup in 
user.ts
 doesn't include Regio_Pressmeet. You'll need to add it. Minor — but it needs to happen.
Decision: Yes
2. tenant field vs existing source field — overlap

Current presmeet handlers already use source="presmeet" on Orders and source="presmeet_config" on Producten for the same purpose as the proposed tenant field. You have two choices:

Replace source with tenant (breaking change, requires migration + handler updates)
Keep both — source for internal presmeet logic (config vs order), tenant for multi-tenancy filtering
I recommend keeping both: tenant for tenant isolation, source for record-type discrimination within presmeet. They serve different purposes.
Decision: Yes

3. Club identity extraction — v1 uses club_* Cognito groups

The existing extract_club_id() function in presmeet_validation.py looks for club_* groups in Cognito. Requirement 2 says store club_id on the Member record instead. This is a good change, but the requirements don't mention a migration path for existing club reps who currently have club_* groups.

Suggestion: Add an acceptance criterion noting that club_* Cognito groups will be deprecated and removed after migration.
Decision: Yes

4. Permission level for PresMeet club users

Current presmeet handlers require events_read permission (which hdcnLeden grants). The requirements say Club_Representatives authenticate with Regio_Pressmeet. But Regio_Pressmeet alone doesn't grant any permissions — it only scopes access regionally.

The requirements need to clarify: Club_Representatives will also have hdcnLeden role (which grants events_read, webshop access, self-service). Regio_Pressmeet is the additional signal that enables the Booking_Form. This is implied but not explicit in the requirements.
Decsion: Club reps get hdcnLeden + Regio_Pressmeet — existing APIs work unchanged since hdcnLeden already grants self-service, webshop, and events_read

5. Dashboard navigation — no Booking_Form card shown

The Dashboard.tsx uses FunctionGuard to control which cards appear. There's currently a /presmeet route but no FunctionGuard-based card for it on the Dashboard. Requirement 10 says show "three functions: self-service profile, webshop, and Booking_Form" — but doesn't specify how the Booking_Form card should be gated.

Suggestion: The Booking_Form card should be gated by Regio_Pressmeet or Regio_All (using FunctionGuard with requiredRoles={['Regio_Pressmeet', 'Regio_All']}).

Decision: Regio_Pressmeet is the sole gate for the Booking_Form — it's checked on the frontend (Dashboard card visibility via FunctionGuard) and on the backend (presmeet booking endpoints)

6. get_presmeet_booking still checks for webmaster role

The existing get_presmeet_booking handler has is_admin = 'webmaster' in user_roles for admin access. Requirement 5 says use Products_CRUD + Regio_Pressmeet instead. This is correct direction — just noting it as a handler that needs updating.
Decision: Clarify please