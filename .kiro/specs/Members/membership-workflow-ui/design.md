# Membership Workflow UI — Design

## 1. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
│                                                                      │
│  MemberAdminTable                    MemberEditView Modal            │
│  ┌────────────────────┐              ┌──────────────────────────┐   │
│  │ ☐ Naam   Status    │              │ Lidmaatschap sectie      │   │
│  │ ☑ Jan    Aangemeld │              │ ┌──────────────────────┐ │   │
│  │ ☑ Piet   Aangemeld │              │ │ Status: [Aangemeld]  │ │   │
│  │ ☐ Kees   Actief    │              │ │                      │ │   │
│  └────────────────────┘              │ │ Acties:              │ │   │
│           │                          │ │ [Goedkeuren]         │ │   │
│           ▼                          │ └──────────────────────┘ │   │
│  ┌────────────────────┐              │                          │   │
│  │ 2 geselecteerd     │              │ Geschiedenis sectie      │   │
│  │ [Goedkeuren ▼]     │              │ ┌──────────────────────┐ │   │
│  │ [Uitvoeren]        │              │ │ ● Aangemeld (24 jul) │ │   │
│  └────────────────────┘              │ │ ○ wachtBetaling      │ │   │
│                                      │ └──────────────────────┘ │   │
└──────────────────┬───────────────────┴──────────┬───────────────────┘
                   │                              │
                   │  POST /members/{id}/         │
                   │       transition             │
                   │  POST /members/              │
                   │       bulk-transition        │
                   ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND                                    │
│                                                                      │
│  transition_member handler                                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ 1. Auth check (Members_CRUD / Members_Status_Approve)         │ │
│  │ 2. Load member from DynamoDB                                   │ │
│  │ 3. Map DynamoDB status → workflow state                        │ │
│  │ 4. membership_engine.execute(state, event, context)            │ │
│  │ 5. dispatcher.execute_transition(transition, result, context)  │ │
│  │ 6. IF success → persist new status + status_history            │ │
│  │ 7. Return result                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│              │                                                       │
│              ▼                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ActionDispatcher (registered implementations)                  │ │
│  │                                                                │ │
│  │ Mandatory Actions:          Side Effects:                      │ │
│  │ • activate_member           • send_welcome_email (SES)         │ │
│  │ • deactivate_member         • send_payment_request (SES)       │ │
│  │ • suspend_member            • send_cancellation_email (SES)    │ │
│  │ • mark_invoice_paid         • notify_admin (SES)               │ │
│  │ • flag_welcome_pack         • audit_log (CloudWatch)           │ │
│  └────────────────────────────────────────────────────────────────┘ │
│              │                                                       │
│              ▼                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │ DynamoDB Members │  │ SES (e-mail)    │  │ CloudWatch Logs   │   │
│  │ + status_history │  │ noreply@h-dcn.nl│  │ WORKFLOW_AUDIT:   │   │
│  └─────────────────┘  └─────────────────┘  └───────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Status Mapping Layer

De workflow engine werkt met `StrEnum` waarden (`applied`, `pending`, `active`, etc.), maar DynamoDB slaat Nederlandse waarden op (`Aangemeld`, `wachtRegio`, `Actief`). Een mapping layer in de handler vertaalt:

```python
# In transition_member/app.py

STATUS_TO_STATE: dict[str, str] = {
    'Aangemeld': MemberState.APPLIED,
    'wachtRegio': MemberState.PENDING,
    'wachtBetaling': MemberState.WAIT_PAYMENT,
    'Actief': MemberState.ACTIVE,
    'Opgezegd': MemberState.CANCELLED,
    'Geschorst': MemberState.SUSPENDED,
}

STATE_TO_STATUS: dict[str, str] = {v: k for k, v in STATUS_TO_STATE.items()}
```

De frontend gebruikt dezelfde mapping in TypeScript:

```typescript
// In config/workflows/membershipWorkflow.ts

export const STATUS_TO_STATE: Record<string, MemberWorkflowState> = {
  Aangemeld: "applied",
  wachtRegio: "pending",
  wachtBetaling: "wait_payment",
  Actief: "active",
  Opgezegd: "cancelled",
  Geschorst: "suspended",
};
```

---

## 3. Frontend Component Structure

```text
frontend/src/
├── config/workflows/
│   ├── index.ts                    # Re-exports
│   ├── types.ts                    # TransitionConfig, WorkflowDefinition
│   └── membershipWorkflow.ts       # States, transitions, labels
│
├── modules/members/
│   ├── components/
│   │   ├── MemberWorkflowPanel.tsx     # NEW — workflow actions in modal
│   │   ├── MemberWorkflowTimeline.tsx  # NEW — status history timeline
│   │   ├── TransitionConfirmDialog.tsx # NEW — confirmation + input dialog
│   │   ├── BulkActionBar.tsx           # NEW — bulk action UI above table
│   │   └── WelcomePackList.tsx         # NEW — pending welcome packs tab
│   └── hooks/
│       └── useMemberTransition.ts      # NEW — API call + state management
│
├── locales/{lang}/workflows.json       # NEW — i18n translations
```

### Component Responsibilities

**MemberWorkflowPanel** — Embedded in MemberEditView modal, replaces free status dropdown:

- Shows current status as a colored badge
- Renders action buttons based on `membershipWorkflow.transitions[currentState]`
- Filters buttons by user role
- Disables buttons when required fields are missing (e.g., `regio`)
- Opens `TransitionConfirmDialog` on click

**TransitionConfirmDialog** — Modal dialog for confirmation:

- Shows what will happen (side effects described in human terms)
- Renders required input fields (e.g., `reason` textarea for SUSPEND)
- Validates inputs before allowing confirmation
- Calls `useMemberTransition` hook on confirm

**BulkActionBar** — Sticky bar above table:

- Shows count of selected members
- Dropdown with available events (intersection of valid events for all selected)
- Execute button → calls bulk endpoint
- Shows result summary dialog

**MemberWorkflowTimeline** — Vertical timeline:

- Reads `status_history` from member record
- Shows each transition as a timeline dot: date, from→to, by whom
- Most recent at top

**WelcomePackList** — Tab in member admin page:

- Lists all members with `welcome_pack_status = 'pending'`
- Shows name, address, lidnummer, activation date
- "Verzonden" button per row
- Bulk "Markeer als verzonden" option

---

## 4. API Endpoints

### POST /members/{member_id}/transition

```
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event": "APPROVE",
  "context": {
    "reason": "Voldoet aan alle voorwaarden"
  }
}
```

Handler: `backend/handler/transition_member/app.py`
Permission: `Members_Transition` (new) or `Members_CRUD`

### POST /members/bulk-transition

```
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "event": "APPROVE",
  "member_ids": ["uuid-1", "uuid-2", "uuid-3"],
  "context": {}
}
```

Handler: `backend/handler/bulk_transition_members/app.py`
Permission: `Members_CRUD`
Max batch size: 25 (DynamoDB batch write limit)

### PUT /members/{member_id}/welcome-pack

```
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "sent"
}
```

Handler: Extends existing `update_member` handler (no new Lambda needed)

---

## 5. E-mail Template Architecture

```text
s3://h-dcn-email-templates/
├── config/
│   └── variables.json              # Shared variables (org name, URLs, etc.)
├── templates/
│   ├── nl/
│   │   ├── membership-application-confirmation.html      # 4.1
│   │   ├── membership-application-admin-notification.html # 4.2
│   │   ├── membership-approved-payment-request.html      # 4.3
│   │   ├── membership-welcome.html                       # 4.4
│   │   ├── membership-cancellation-confirmation.html     # 4.5
│   │   └── membership-suspension-notice.html             # 4.6
│   ├── en/
│   │   └── ... (same files, English)
│   ├── de/
│   │   └── ... (same files, German)
│   └── ... (fr, es, it, da, sv)
```

### Template variable sources

| Variabele             | Bron                                                          |
| --------------------- | ------------------------------------------------------------- |
| `MEMBER_NAME`         | `voornaam` + `tussenvoegsel` + `achternaam` uit Members tabel |
| `MEMBER_NUMBER`       | `lidnummer` uit Members tabel                                 |
| `EMAIL`               | `email` uit Members tabel                                     |
| `REGIO`               | `regio` uit Members tabel                                     |
| `MEMBERSHIP_TYPE`     | `lidmaatschap` uit Members tabel                              |
| `APPLICATION_DATE`    | `created` timestamp                                           |
| `CONTRIBUTION_AMOUNT` | Afgeleid van `lidmaatschap` type                              |
| `PAYMENT_DEADLINE`    | `created` + 30 dagen                                          |
| `IBAN`                | Organisatie IBAN (uit env var)                                |
| `REFERENCE`           | `lidnummer` of gegenereerde referentie                        |
| `CANCELLATION_DATE`   | Transitie timestamp                                           |
| `SUSPENSION_DATE`     | Transitie timestamp                                           |
| `REASON`              | Uit `context.reason` in transitie                             |
| `REGIO_CONTACT_NAME`  | Uit regio-configuratie                                        |
| `REGIO_CONTACT_EMAIL` | Uit regio-configuratie                                        |
| `PORTAL_URL`          | `ORGANIZATION_WEBSITE` uit variables.json                     |
| `WELCOME_PACK_NOTE`   | Statische tekst over post-verzending                          |
| `ORGANIZATION_*`      | Uit variables.json (bestaand)                                 |

### E-mail verzending

Hergebruikt het bestaande patroon uit `send_delegate_invitation`:

```python
ses_client = boto3.client('ses', region_name='eu-west-1')

ses_client.send_email(
    Source='noreply@h-dcn.nl',
    Destination={'ToAddresses': [recipient_email]},
    Message={
        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
        'Body': {'Html': {'Data': rendered_html, 'Charset': 'UTF-8'}},
    },
)
```

### Locale resolution

De taal van de e-mail wordt bepaald door:

1. `preferred_locale` veld op het lid-record (indien aanwezig)
2. Fallback: `nl` (Nederlands)

---

## 6. Welkomstpakket Tracking

### DynamoDB velden (toe te voegen aan Members tabel)

| Veld                     | Type   | Beschrijving                                  |
| ------------------------ | ------ | --------------------------------------------- |
| `welcome_pack_status`    | String | `pending` / `sent` / `not_applicable`         |
| `welcome_pack_sent_date` | String | ISO datum van verzending                      |
| `welcome_pack_sent_by`   | String | Email van admin die verzending markeert       |
| `welcome_pack_notes`     | String | Optionele notities (bijv. "adres onvolledig") |

### Workflow integratie

De `flag_welcome_pack` actie is een **mandatory action** in de PAYMENT_RECEIVED transitie:

```python
def flag_welcome_pack(ctx: dict) -> None:
    """Set welcome_pack_status to pending on activation."""
    member_id = ctx['member_id']
    member = ctx.get('member', {})

    # Validate address
    has_address = (
        (member.get('straat') or member.get('postadres')) and
        (member.get('postcode') or member.get('postpostcode')) and
        (member.get('woonplaats') or member.get('postwoonplaats'))
    )

    notes = None if has_address else 'Adres onvolledig — controleer voor verzending'

    update_expression = 'SET welcome_pack_status = :status'
    expression_values = {':status': 'pending'}

    if notes:
        update_expression += ', welcome_pack_notes = :notes'
        expression_values[':notes'] = notes

    table.update_item(
        Key={'member_id': member_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
    )
```

### Admin UI flow

```text
Admin opent "Welkomstpakketten" tab
    │
    ▼
Tabel toont leden met welcome_pack_status = 'pending'
    │
    ├── Kolommen: Naam, Lidnummer, Adres, Activatiedatum, Notities
    │
    ├── ⚠️ Rij met "Adres onvolledig" notitie → oranje highlight
    │
    └── Admin print brief, stopt in envelop met stickers + badge
          │
          ▼
    Klikt "Verzonden" → PUT /members/{id}/welcome-pack { status: "sent" }
          │
          ▼
    Rij verdwijnt uit de lijst
```

---

## 7. Transition Flow Diagrams

### Enkele transitie (admin keurt lid goed)

```text
Admin klikt "Goedkeuren" in MemberWorkflowPanel
    │
    ▼
TransitionConfirmDialog opent
    │ "Wil je dit lid goedkeuren?"
    │ "Er wordt een betalingsverzoek verstuurd."
    │
    │ [Annuleren] [Bevestigen]
    │                    │
    │                    ▼
    │  useMemberTransition.mutate({ event: 'APPROVE' })
    │                    │
    │                    ▼
    │  POST /members/{id}/transition { event: "APPROVE" }
    │                    │
    │                    ▼
    │  Backend:
    │  1. Load member → status = "Aangemeld"
    │  2. Map → state = "applied"
    │  3. engine.execute("applied", "APPROVE") → success
    │  4. dispatcher: (geen mandatory actions voor APPROVE)
    │  5. side effects: send_payment_request ✓, audit_log ✓
    │  6. Persist: status = "wachtBetaling", status_history += entry
    │  7. Response: { success: true, new_status: "wachtBetaling" }
    │                    │
    │                    ▼
    │  Frontend:
    │  - Toast: "Lid goedgekeurd. Betalingsverzoek verstuurd."
    │  - Badge update → "wachtBetaling"
    │  - Timeline entry verschijnt
    │  - Member list refresht
    │
    └── (klaar)
```

### Bulk transitie (8 aanmeldingen goedkeuren)

```text
Admin filtert tabel op status = "Aangemeld"
    │
    ▼
Selecteert 8 leden via checkboxes
    │
    ▼
BulkActionBar verschijnt: "8 leden geselecteerd"
    │ Dropdown: [Goedkeuren]  (enige geldige actie voor status "Aangemeld")
    │
    │ Klikt [Uitvoeren]
    │         │
    │         ▼
    │ Bevestigingsdialoog: "8 leden goedkeuren?"
    │         │
    │         ▼ [Bevestigen]
    │
    │  POST /members/bulk-transition
    │  { event: "APPROVE", member_ids: [...8 ids...] }
    │         │
    │         ▼
    │  Backend: per lid onafhankelijk verwerken
    │  - lid 1: ✓ (regio ingevuld)
    │  - lid 2: ✓
    │  - lid 3: ✗ (regio ontbreekt → guard faalt)
    │  - lid 4-8: ✓
    │         │
    │         ▼
    │  Response: { total: 8, succeeded: 7, failed: 1, results: [...] }
    │         │
    │         ▼
    │  Frontend toont resultaat-samenvatting:
    │  ┌──────────────────────────────────────────┐
    │  │ ✓ 7 leden succesvol goedgekeurd          │
    │  │ ✗ 1 mislukt:                             │
    │  │   • Piet Jansen — regio ontbreekt        │
    │  │                                          │
    │  │ [Sluiten]  [Bekijk mislukte]             │
    │  └──────────────────────────────────────────┘
    │
    └── Tabel refresht — 7 leden nu in "wachtBetaling"
```

---

## 8. Permission Model

| Actie                   | Rol                                      | Check moment         |
| ----------------------- | ---------------------------------------- | -------------------- |
| Workflow knoppen zien   | `Members_CRUD`, `Members_Status_Approve` | Frontend (UI filter) |
| Transitie uitvoeren     | `Members_CRUD`, `Members_Status_Approve` | Backend (auth check) |
| Bulk transitie          | `Members_CRUD`                           | Backend              |
| Welkomstpakket markeren | `Members_CRUD`                           | Backend              |
| Status history bekijken | `Members_Read`, `Members_CRUD`           | Frontend (UI filter) |

---

## 9. SAM Template Additions

```yaml
# New Lambda function
TransitionMemberFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: handler/transition_member
    Handler: app.lambda_handler
    Runtime: python3.11
    Layers:
      - !Ref AuthLayer
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref MembersTable
      - Statement:
          - Effect: Allow
            Action:
              - ses:SendEmail
            Resource: "*"
      - Statement:
          - Effect: Allow
            Action:
              - cognito-idp:AdminAddUserToGroup
              - cognito-idp:AdminRemoveUserFromGroup
            Resource: !Sub "arn:aws:cognito-idp:${AWS::Region}:${AWS::AccountId}:userpool/*"
      - Statement:
          - Effect: Allow
            Action:
              - s3:GetObject
            Resource: !Sub "${EmailTemplatesBucket.Arn}/*"
    Environment:
      Variables:
        MEMBERS_TABLE_NAME: !Ref MembersTable
        EMAIL_TEMPLATES_BUCKET: !Ref EmailTemplatesBucket
        SENDER_EMAIL: noreply@h-dcn.nl
        COGNITO_USER_POOL_ID: !Ref ExistingUserPoolId
    Events:
      TransitionMember:
        Type: Api
        Properties:
          Path: /members/{member_id}/transition
          Method: post
          RestApiId: !Ref ApiGateway

BulkTransitionMembersFunction:
  Type: AWS::Serverless::Function
  Properties:
    CodeUri: handler/bulk_transition_members
    Handler: app.lambda_handler
    Runtime: python3.11
    Layers:
      - !Ref AuthLayer
    # Same policies as TransitionMemberFunction
    Events:
      BulkTransition:
        Type: Api
        Properties:
          Path: /members/bulk-transition
          Method: post
          RestApiId: !Ref ApiGateway
```

---

## 10. Data Migration Considerations

Bestaande leden hebben geen `status_history` of `welcome_pack_status`. Dit is acceptabel:

- `status_history`: leeg array → timeline toont "Geen geschiedenis beschikbaar"
- `welcome_pack_status`: afwezig → niet tonen in welkomstpakket-lijst
- Alleen NIEUWE activeringen na deploy triggeren het welkomstpakket-tracking

Een migratiescript is NIET nodig voor de initiële deploy. Historische data kan later optioneel geback-filled worden uit CloudWatch logs.

---

## 11. Error Handling Strategy

| Fout                     | Frontend gedrag                                      | Backend response    |
| ------------------------ | ---------------------------------------------------- | ------------------- |
| Ongeldige transitie      | Toast: "Deze actie is niet mogelijk vanuit status X" | 400 + error message |
| Guard gefaald            | Toast: specifieke melding (bijv. "Reden ontbreekt")  | 400 + guard error   |
| Mandatory action gefaald | Toast: "Actie mislukt: [details]"                    | 500 + action error  |
| SES fout (side effect)   | Niets — transitie is succesvol                       | 200 + failures list |
| Lid niet gevonden        | Toast: "Lid niet gevonden"                           | 404                 |
| Geen permissie           | Knoppen niet zichtbaar / disabled                    | 403                 |
| Netwerk fout             | Toast: "Verbinding mislukt, probeer opnieuw"         | —                   |

---

## 12. Future: Status Waarde Migratie

Op termijn kan overwogen worden om de DynamoDB `status` waarden te migreren naar de Engelse workflow-waarden (`active` i.p.v. `Actief`). Dit is NIET onderdeel van deze spec — de mapping layer houdt het werkbaar. Een aparte migratie-spec kan dit adresseren wanneer:

- De mapping-complexiteit oploopt
- Er een API publiek wordt gemaakt
- Er internationalisering van backend responses nodig is
