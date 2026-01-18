# Member Self-Service Field Alignment

## Overview

This document shows the alignment between frontend field configuration and backend allowed fields for member self-service updates.

## Section Structure

The member form is organized into 6 sections as defined in `frontend/src/config/memberFields.ts`:

### 1. Persoonlijke Informatie (Personal Information)

**Frontend fields with `selfService: true`:**

- voornaam (First name)
- achternaam (Last name)
- initialen (Initials)
- tussenvoegsel (Name prefix)
- geboortedatum (Birth date)
- geslacht (Gender)
- ~~email (Email)~~ - **PROTECTED** (tied to Cognito account)
- telefoon (Phone)
- minderjarigNaam (Parent/Guardian name - conditional)

**Backend allowed fields:** ✅ All included (email excluded - protected)

### 2. Adresgegevens (Address Information)

**Frontend fields with `selfService: true`:**

- straat (Street + house number)
- postcode (Postal code)
- woonplaats (City)
- land (Country)

**Backend allowed fields:** ✅ All included

### 3. Lidmaatschap (Membership)

**Frontend fields with `selfService: true`:**

- privacy (Privacy consent)
- clubblad (Club magazine preference)
- nieuwsbrief (Newsletter preference)
- wiewatwaar (How they found us)

**Protected fields (admin-only):**

- status (Membership status)
- lidmaatschap (Membership type)
- regio (Region)
- ingangsdatum (Start date)
- lidnummer (Member number)

**Backend allowed fields:** ✅ Only self-service preferences included

### 4. Motorgegevens (Motorcycle Information)

**Frontend fields with `selfService: true`:**

- motormerk (Motorcycle brand)
- motortype (Motorcycle type)
- bouwjaar (Build year)
- kenteken (License plate)

**Backend allowed fields:** ✅ All included

### 5. Financiële Gegevens (Financial Information)

**Frontend fields with `selfService: true`:**

- betaalwijze (Payment method)
- bankrekeningnummer (Bank account number)

**Backend allowed fields:** ✅ All included

### 6. Administratieve Gegevens (Administrative Information)

**All fields are read-only or admin-only:**

- created_at (Record created)
- updated_at (Last updated)
- notities (Notes)

**Backend allowed fields:** ✅ None (all protected)

## Backend Implementation

Location: `backend/handler/get_member_self/app.py`

The `update_own_member_data()` function:

1. Validates that only allowed fields are updated
2. Fetches the complete updated member record after update
3. Returns the full member data (not just a success message)

## Frontend Implementation

Location: `frontend/src/components/MemberSelfServiceView.tsx`

The component:

1. Renders fields based on `selfService` permission
2. Shows editable fields with white background
3. Shows read-only fields with gray background
4. Receives complete member data after save and updates the form

## Fix Applied

**Problem:** After saving, the form showed empty fields because backend returned:

```json
{
  "message": "Member data updated successfully",
  "updated_fields": ["voornaam", "achternaam"]
}
```

**Solution:** Backend now returns complete member data:

```json
{
  "member_id": "123",
  "voornaam": "Jan",
  "achternaam": "Jansen",
  "lidmaatschap": "Lid",
  "regio": "Noord",
  ...all other fields...
}
```

## Status

✅ Backend returns complete member data after update
✅ Backend allowed fields match frontend selfService permissions
✅ Section grouping documented and aligned
✅ Protected fields (status, lidmaatschap, regio) excluded from self-service

Ready for deployment and testing!
