# Type Safety & Validation Strategy

## Backend (Python)

### Type Hints — Incremental Adoption

- **Nieuwe code**: 100% type hints verplicht
- **Meest gewijzigde bestanden**: prioriteit voor toevoegen van type hints
- **Shared layer (`auth_utils.py`)**: hoge prioriteit (propageert naar alle handlers)
- **Stabiele, ongewijzigde handlers**: laat met rust

### Geen Pydantic

Pydantic voegt onvoldoende waarde toe voor deze codebase:

- Handlers zijn klein (1 endpoint per Lambda) — handmatige validatie is voldoende leesbaar
- Geen FastAPI integratie (waar Pydantic het meest schittert)
- Cold start penalty (~50-100ms extra import time per Lambda)
- DynamoDB `Decimal` type conflicteert met Pydantic zonder custom validators
- Field Registry is al de bron van waarheid — Pydantic zou een tweede validatieplek creëren

### Wel: TypedDict + validate-functies

```python
from typing import TypedDict, NotRequired
from decimal import Decimal

class ProductUpdate(TypedDict):
    product_id: str
    prijs: Decimal
    naam: NotRequired[str]
    active: NotRequired[bool]

def validate_product_update(body: dict) -> tuple[ProductUpdate | None, str | None]:
    """Validate en retourneer typed dict, of error message."""
    if 'product_id' not in body:
        return None, "product_id is required"
    if 'prijs' in body:
        try:
            body['prijs'] = Decimal(str(body['prijs']))
        except (ValueError, TypeError):
            return None, "prijs must be numeric"
    return body, None
```

Voordelen:

- Type safety (Pyright checkt het)
- Runtime validatie (expliciet, geen magic)
- Zero extra dependencies
- Geen cold start penalty

### Tooling

- **Pyright** in `basic` mode voor type checking
- Per-handler override mogelijk via `pyrightconfig.json` als nodig

## Frontend (TypeScript)

### Validatie-lagen (elk met eigen doel)

| Laag         | Tool                  | Doel                                 |
| ------------ | --------------------- | ------------------------------------ |
| Form UI      | Formik + Yup          | Directe feedback aan gebruiker       |
| Compile-time | TypeScript interfaces | Correctheid van code                 |
| Runtime API  | Backend validatie     | Bescherming tegen ongeldige requests |

### Belangrijke regels

- Yup draait client-side — backend MOET altijd zelf valideren
- Field Registry blijft de single source of truth voor validatieregels
- TypeScript interfaces moeten aansluiten op de Field Registry types
- Geen runtime validatie-libraries op de frontend naast Yup (geen zod, io-ts, etc.)

## Heroverweging triggers

Pydantic wordt pas relevant als:

- Er een gedeelde API-laag/SDK komt die meerdere handlers bedient
- Er een migratie naar FastAPI plaatsvindt
- Er complexe nested payloads ontstaan die handmatige validatie onleesbaar maken
