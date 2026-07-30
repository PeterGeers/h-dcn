# Workflow Framework — Requirements

## Context

De H-DCN codebase heeft meerdere plekken waar status-transities plaatsvinden (orders, members, events), elk met hun eigen ad-hoc validatie. Er is geen gedeeld mechanisme voor:

- Transitie-validatie (mag deze statuswijziging?)
- Side-effect uitvoering (email, audit, stock update)
- Foutafhandeling (wat als een actie faalt halverwege?)

Dit spec definieert een lichtgewicht workflow engine als gedeelde component in de Lambda Layer.

Referentie: #[[file:.kiro/specs/Workflow framework/recommended.md]]

---

## Traceability Matrix

| Requirement                                 | recommended.md Section                         | Status |
| ------------------------------------------- | ---------------------------------------------- | ------ |
| 1.1 Engine operaties                        | Engine Implementation                          | ▶ TODO |
| 1.2 TransitionResult                        | Core Types                                     | ▶ TODO |
| 1.3 Engine crasht nooit                     | Engine Implementation                          | ▶ TODO |
| 1.4 Geen AWS kennis in engine               | Design Principles #1                           | ▶ TODO |
| 2.1 Transitie TypedDict                     | Core Types                                     | ▶ TODO |
| 2.2 Python bestanden (geen JSON/DB)         | Defining & Updating Workflows                  | ▶ TODO |
| 2.3 StrEnum states/events                   | State & Event Enums                            | ▶ TODO |
| 2.4 Named guards (geen lambdas)             | Guard Functions                                | ▶ TODO |
| 3.1 ActionDispatcher class                  | Action Dispatcher                              | ▶ TODO |
| 3.2 Mandatory actions falen → rollback      | Failure Handling                               | ▶ TODO |
| 3.3 Side effects falen → non-blocking       | Failure Handling                               | ▶ TODO |
| 3.4 Register via register/register_many     | Action Dispatcher                              | ▶ TODO |
| 3.5 Onbekende acties = fout                 | Action Dispatcher                              | ▶ TODO |
| 4.1 Persist NA mandatory actions            | Usage in a Handler                             | ▶ TODO |
| 4.2 Engine/dispatcher schrijft niet naar DB | Design Principles #1, #2                       | ▶ TODO |
| 4.3 Status op entity record                 | Design Principles #6                           | ▶ TODO |
| 5.1 WORKFLOW_AUDIT prefix                   | Audit Logging Strategy                         | ▶ TODO |
| 5.2 Audit log velden                        | Audit Logging Strategy                         | ▶ TODO |
| 5.3 Zelfde print-pattern als bestaand       | Audit Logging Strategy                         | ▶ TODO |
| 5.4 Audit = side effect                     | Audit Logging Strategy                         | ▶ TODO |
| 6.1 Membership workflow                     | Example: Membership Workflow                   | ▶ TODO |
| 6.2 Order workflow                          | Example: Order Workflow                        | ▶ TODO |
| 7.1 Locatie in shared layer                 | Where This Lives                               | ▶ TODO |
| 7.2 Module bestanden                        | Where This Lives                               | ▶ TODO |
| 8.1 Unit tests engine                       | Testing Strategy                               | ▶ TODO |
| 8.2 Dispatcher tests                        | Testing Strategy                               | ▶ TODO |
| 8.3 Property tests (Hypothesis)             | Testing Strategy                               | ▶ TODO |
| 9.1 Trigger via handler                     | Trigger Patterns                               | ▶ TODO |
| 9.2 Webhook trigger                         | Trigger Patterns: Pattern 2                    | ▶ TODO |
| 9.3 Scheduled trigger                       | Trigger Patterns: Pattern 3                    | ▶ TODO |
| 9.4 Multi-entity event handling             | Trigger Patterns: One event, multiple entities | ▶ TODO |
| 10.1 Rollback bij partial failure           | Failure Handling                               | ▶ TODO |
| 10.2 Compensatie-acties optioneel           | Failure Handling                               | ▶ TODO |
| 11.1 Async action via Lambda invoke         | What This Does NOT Cover                       | ▶ TODO |
| 11.2 Sync = default                         | What This Does NOT Cover                       | ▶ TODO |

---

## Requirements

### 1. Workflow Engine (Core)

**1.1** Het systeem MOET een `WorkflowEngine` class bieden die een lijst van transitie-definities accepteert en drie operaties ondersteunt:

- `can_transition(current_state, event, context)` → controleert of een transitie is toegestaan
- `execute(current_state, event, context)` → voert de transitie uit en retourneert een `TransitionResult`
- `get_allowed_events(current_state)` → retourneert alle geldige events vanuit een bepaalde state

**1.2** De engine MOET een `TransitionResult` dataclass retourneren met:

- `success: bool`
- `old_state: str`
- `new_state: str | None`
- `event: str`
- `actions_executed: list[str]`
- `side_effects_executed: list[str]`
- `failures: list[str]`
- `error: str | None`

**1.3** De engine MOET nooit een exception raisen — ongeldige transities retourneren `success=False` met een error message.

**1.4** De engine MAG geen kennis hebben van AWS services (geen boto3, geen SES, geen DynamoDB imports).

---

### 2. Transitie-definities

**2.1** Elke transitie MOET gedefinieerd worden als een Python `TypedDict` met:

- `from_state: str` — de huidige status
- `to_state: str` — de nieuwe status na transitie
- `event: str` — het event dat de transitie triggert
- `guard: Callable | None` (optioneel) — voorwaarde die `True` moet retourneren
- `actions: list[str]` — verplichte acties (moeten allemaal slagen)
- `side_effects: list[str]` — optionele acties (best-effort, falen blokkeert niet)

**2.2** Transities MOETEN gedefinieerd worden in Python bestanden (niet JSON, niet DynamoDB). Dit geeft type-checking, IDE support, en git history.

**2.3** States en events MOETEN gedefinieerd worden als `StrEnum` classes — geen magic strings.

**2.4** Guards MOETEN benoemde functies zijn (geen lambdas) met een beschrijvende docstring.

---

### 3. Action Dispatcher

**3.1** Het systeem MOET een `ActionDispatcher` class bieden die named actions uitvoert.

**3.2** Mandatory actions (`actions` in de transitie):

- MOETEN allemaal slagen voordat de state wordt gepersisteerd
- Bij falen: `result.success = False`, `result.new_state = None`
- Resterende mandatory actions worden overgeslagen
- Side effects worden NIET uitgevoerd

**3.3** Side effects (`side_effects` in de transitie):

- Worden uitgevoerd na succesvolle mandatory actions
- Falen wordt gelogd in `result.failures` maar blokkeert de transitie NIET
- `result.success` blijft `True`

**3.4** De dispatcher MOET acties registreren via `register(name, fn)` of `register_many(dict)`.

**3.5** Onbekende actie-namen MOETEN behandeld worden als fout (niet stilzwijgend genegeerd).

---

### 4. Persistence Pattern

**4.1** De DynamoDB status-update MOET pas plaatsvinden NADAT alle mandatory actions succesvol zijn uitgevoerd.

**4.2** De handler is verantwoordelijk voor het persisteren — de engine en dispatcher schrijven NIET naar DynamoDB.

**4.3** De status wordt opgeslagen op het entity record zelf (geen aparte WorkflowInstances tabel).

---

### 5. Audit Logging

**5.1** Elke workflow transitie MOET gelogd worden via `WORKFLOW_AUDIT:` prefix naar CloudWatch Logs.

**5.2** De audit log MOET bevatten: entity_type, entity_id, old_state, new_state, event, user_email, actions_executed, failures, timestamp.

**5.3** De audit log volgt hetzelfde `print(f"PREFIX: {json.dumps(...)}")` patroon als de bestaande `ACCESS_AUDIT:` en `AUDIT_LOG:` prefixes.

**5.4** Audit logging is een side effect — het falen ervan blokkeert de transitie NIET.

---

### 6. Initial Workflows

**6.1** Membership workflow MOET gedefinieerd worden met minimaal:

- pending → wait_payment (APPROVE)
- wait_payment → active (PAYMENT_RECEIVED)
- active → cancelled (CANCEL)
- active → suspended (SUSPEND, guard: requires_reason)

**6.2** Order workflow MOET gedefinieerd worden met minimaal:

- draft → submitted (SUBMIT, guard: has_stock_available)
- submitted → paid (PAYMENT_RECEIVED)
- paid → fulfilled (FULFILL)
- submitted → cancelled (CANCEL)
- paid → refunded (REFUND, guard: is_refundable)

---

### 7. Locatie in de Codebase

**7.1** De workflow engine MOET leven in de shared Lambda Layer: `backend/layers/auth-layer/python/shared/workflows/`

**7.2** De module MOET de volgende bestanden bevatten:

- `__init__.py`
- `types.py` — Transition TypedDict, TransitionResult dataclass
- `states.py` — StrEnum classes voor alle states en events
- `guards.py` — Named guard functies
- `engine.py` — WorkflowEngine class
- `dispatcher.py` — ActionDispatcher class
- `audit.py` — write_workflow_audit functie
- `membership.py` — Membership transitie-configuratie
- `orders.py` — Order transitie-configuratie

---

### 8. Testing

**8.1** De engine MOET unit tests hebben die geldige transities, ongeldige transities, en guards verifiëren.

**8.2** De dispatcher MOET tests hebben die het verschil tussen mandatory action failure en side effect failure aantonen.

**8.3** Er MOETEN property-based tests (Hypothesis) zijn die bewijzen dat de engine nooit crasht ongeacht input.

---

### 9. Trigger Patterns

**9.1** De engine wordt altijd aangeroepen vanuit een Lambda handler — de engine luistert NIET zelf naar events, queues, of schedules.

**9.2** Webhook-geïnitieerde transities (bijv. Stripe payment confirmation) MOETEN via een dedicated webhook handler lopen die de engine aanroept.

**9.3** Tijd-gebaseerde transities (bijv. membership expiry) MOETEN via een scheduled Lambda handler lopen die entities scant en per entity de engine aanroept.

**9.4** Wanneer één real-world event meerdere entities raakt (bijv. betaling triggert zowel order update als membership activatie), MOET de handler beide engines sequentieel aanroepen. Async fan-out of EventBridge is pas nodig als dit te complex wordt.

---

### 10. Rollback bij Partial Failure

**10.1** Wanneer mandatory action N faalt maar acties 1..(N-1) al zijn uitgevoerd, MOET de `TransitionResult` alle uitgevoerde acties rapporteren in `actions_executed` en de fout in `failures`.

**10.2** Compensatie-acties (rollback van eerder uitgevoerde acties) zijn OPTIONEEL in de eerste implementatie. De handler MAG zelf compensatie uitvoeren op basis van `result.actions_executed`. Een formeel compensatie-mechanisme in de engine is toekomstig werk.

---

### 11. Async Actions

**11.1** Individuele acties MOGEN geregistreerd worden als async (fire-and-forget Lambda invoke). Dit is nuttig voor langlopende operaties zoals PDF-generatie.

**11.2** Standaard draait alles synchroon — async is opt-in per actie-registratie, niet een engine-feature.

---

## Niet in scope

- Frontend integratie (get_allowed_events in API responses) — toekomstige fase
- WorkflowService facade — extract wanneer 3+ handlers het patroon herhalen
- Multi-tenancy / workflow_name op entities — pas relevant bij SaaS
- Migratie van bestaande handlers — apart per handler in volgende specs
- EventBridge integratie — pas bij meerdere onafhankelijke consumers
