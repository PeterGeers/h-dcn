# De-activate & Suspend Member — TODO

## De-activate (Opzeggen)

Wanneer een lid wordt gedeactiveerd:

1. **Verwijder alle persoonlijke gegevens** — voornaam, achternaam, adres, telefoon, geboortedatum, motorgegevens, bankgegevens (AVG/GDPR compliance)
2. **Voeg een deactivatie-datum toe** — `deactivated_at` met de huidige datum
3. **Bewaar lidmaatschapsgegevens** — lidnummer, ingangsdatum, regio, lidmaatschap-type, jaren_lid
4. **Zet status op `Opgezegd`**
5. **Verwijder uit Cognito groep `hdcnLeden`** (al geïmplementeerd)
6. **Verwijder Cognito account** (of markeer als disabled)

## Suspend (Schorsen)

Wanneer een lid wordt geschorst:

1. **Bewaar alle gegevens** — persoonlijke data blijft intact (schorsing is tijdelijk)
2. **Voeg een schorsings-datum toe** — `suspended_at` met de huidige datum
3. **Bewaar schorsingsreden** — `suspension_reason` (al geïmplementeerd)
4. **Zet status op `Geschorst`**
5. **Verwijder uit Cognito groep `hdcnLeden`** (blokkeer portal toegang)

## Verschil

| Aspect            | De-activate                 | Suspend          |
| ----------------- | --------------------------- | ---------------- |
| Persoonlijke data | Verwijderd (GDPR)           | Bewaard          |
| Lidmaatschapsdata | Bewaard                     | Bewaard          |
| Cognito account   | Verwijderd/disabled         | Groep verwijderd |
| Omkeerbaar        | Nee (herinschrijving nodig) | Ja (REACTIVATE)  |
| Status            | Opgezegd                    | Geschorst        |
