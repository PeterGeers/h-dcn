# EPC QR Code voor Betaalinstructies — TODO

## Doel

Een EPC QR code toevoegen aan de betaalinstructie-email zodat nieuwe leden met hun bank-app kunnen scannen en de betaling direct wordt voorgevuld.

## EPC QR Code Standaard

De European Payments Council (EPC) QR code is een standaard die door vrijwel alle Europese bank-apps wordt herkend (ING, Rabo, ABN, SNS, Bunq, etc.).

Format (platte tekst gecodeerd als QR):

```
BCD
002
1
SCT
[BIC]
[Naam begunstigde]
[IBAN]
EUR[bedrag]


[Betalingsreferentie]
```

Voorbeeld:

```
BCD
002
1
SCT
INGBNL2A
Harley-Davidson Club Nederland
NL12INGB0001234567
EUR50.00


HDCN-Geers-e6a5912c
```

## Implementatie-opties

### Optie A: Backend (in email)

- Genereer QR code als PNG in de Lambda (Python `qrcode` library)
- Embed als inline afbeelding (CID) of als bijlage in de SES email
- Voordeel: werkt direct vanuit de email
- Nadeel: SES email complexiteit (multipart MIME)

### Optie B: Frontend (in portal)

- Toon QR code op de "Wacht op betaling" status pagina in MyAccount
- Gebruik `qrcode.react` of `qrcode` npm package
- Voordeel: simpeler, geen email bijlage nodig
- Nadeel: lid moet inloggen om het te zien

### Aanbeveling

Combinatie: QR code in de email (optie A) + op de portal status pagina (optie B).

## Benodigde gegevens

- BIC code van H-DCN bankrekening
- Correct IBAN (niet de placeholder NL00INGB0000000000)
- Bedrag (uit CONTRIBUTION_AMOUNTS mapping)
- Referentie (korte variant: HDCN-achternaam-8chars)

## Prioriteit

Middel — verbetert de betaalervaring significant maar is niet blokkerend.
