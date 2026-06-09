# Bugfix Requirements Document

## Introduction

Two related bugs in the event administration module prevent users with Events_CRUD permission from managing events properly:

1. **Edit/Delete events fails with "no rights" error** — The frontend `FunctionPermissionManager.hasAccess()` method does not recognize the `'all'` permission level for the `Events_CRUD` role, causing it to deny write access even though the user has full event management permissions. This makes the edit and delete buttons appear disabled or show a "Geen rechten" (no rights) toast.

2. **Copy event modal: fields not editable and save fails** — When duplicating an event, the `handleDuplicate` function creates a copy object with `title` set to `"[name] (Kopie)"` but maps it incorrectly (using `title` key while the source data may only have `naam`). Additionally, the `event_date` is deliberately cleared for the copy, but the form's `useEffect` dependency on `allowedRegions` may cause re-renders that reset form state, making fields appear unresponsive. The save then fails validation because `event_date` is required but was cleared without prompting the user to fill it in before submission.

Both bugs affect users with the `Events_CRUD` + `Regio_All` role combination (system administrators with full access).

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user with Events_CRUD and Regio_All roles clicks the edit button on an event THEN the system shows "Geen rechten om te bewerken" toast because `FunctionPermissionManager.hasAccess('events', 'write')` returns false

1.2 WHEN a user with Events_CRUD and Regio_All roles clicks the delete button on an event THEN the system shows "Geen rechten om te verwijderen" toast because `permissionManager?.hasAccess('events', 'write')` returns false in `canDeleteEvent`

1.3 WHEN a user with Events_CRUD permission duplicates an event THEN the copy modal text input fields do not respond to user input due to form state being reset by `useEffect` re-renders triggered by `allowedRegions` dependency changes

1.4 WHEN a user with Events_CRUD permission attempts to save a duplicated event THEN the system fails validation with "Naam en startdatum zijn verplicht" because `event_date` is cleared in the duplicate object and form state may be reset before the user can fill it in

### Expected Behavior (Correct)

2.1 WHEN a user with Events_CRUD and Regio_All roles clicks the edit button on an event THEN the system SHALL open the event edit form with the event data pre-populated and all fields editable

2.2 WHEN a user with Events_CRUD and Regio_All roles clicks the delete button on an event THEN the system SHALL show a confirmation dialog and delete the event upon confirmation

2.3 WHEN a user with Events_CRUD permission duplicates an event THEN the system SHALL open the event form modal with all text fields editable, pre-populated with the source event data (with title suffixed "(Kopie)" and dates cleared for the user to fill in)

2.4 WHEN a user with Events_CRUD permission fills in the required fields on a duplicated event form and clicks save THEN the system SHALL create a new event with the provided data

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user without Events_CRUD or Events_Read permission attempts to access the event admin page THEN the system SHALL CONTINUE TO show the access denied message

3.2 WHEN a user with only Events_Read permission attempts to edit or delete an event THEN the system SHALL CONTINUE TO show disabled edit/delete buttons with "Geen rechten" tooltip

3.3 WHEN a user with regional-only access (e.g., Regio_Utrecht without Regio_All) attempts to edit an event from another region THEN the system SHALL CONTINUE TO deny access based on regional restrictions

3.4 WHEN a user with Events_CRUD creates a new event (not a duplicate) THEN the system SHALL CONTINUE TO require name and start date validation before saving

3.5 WHEN a user with Events_Read (but not Events_CRUD) views events THEN the system SHALL CONTINUE TO display financial data (costs, revenue, profit) in the event list as read-only

3.6 WHEN the backend receives an event update/delete request without valid Events_CRUD permission THEN the system SHALL CONTINUE TO return a 403 Forbidden response

---

## Bug Condition (Formal)

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type EventAdminAction
  OUTPUT: boolean

  // Bug 1: Permission check failure for users with Events_CRUD
  LET hasEventsCRUD = "Events_CRUD" IN X.userRoles
  LET hasRegioAll = "Regio_All" IN X.userRoles
  LET actionIsWriteCheck = X.action IN {"edit", "delete", "duplicate"}

  RETURN hasEventsCRUD AND hasRegioAll AND actionIsWriteCheck
END FUNCTION
```

### Property: Fix Checking

```pascal
// Property: Fix Checking - Events_CRUD users can edit/delete/duplicate events
FOR ALL X WHERE isBugCondition(X) DO
  result ← permissionManager.hasAccess('events', 'write')
  ASSERT result = true

  // For duplicate action specifically:
  IF X.action = "duplicate" THEN
    formState ← openDuplicateForm(X.sourceEvent)
    ASSERT formState.fieldsEditable = true
    ASSERT formState.canSaveWhenFieldsFilled = true
  END IF
END FOR
```

### Property: Preservation Checking

```pascal
// Property: Preservation Checking
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT F(X) = F'(X)
  // Users without Events_CRUD still get denied
  // Regional restrictions still apply
  // Validation rules for new events still apply
END FOR
```
