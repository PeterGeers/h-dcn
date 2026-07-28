# Welkomstbrief PDF — TODO

## Doel

Bij het verzenden van een welkomstpakket moet een PDF welkomstbrief gegenereerd kunnen worden met de gegevens van het nieuwe lid. Deze brief wordt afgedrukt en bij het pakket gevoegd.

## Inhoud PDF

- **Geadresseerde:** Naam + adres van het nieuwe lid
- **Datum:** Huidige datum
- **Aanhef:** Beste [voornaam],
- **Tekst:** Welkomstbericht met:
  - Lidnummer
  - Regio
  - Contactgegevens regio-secretaris
  - Verwijzing naar portal (portal.h-dcn.nl)
  - Korte uitleg wat er in het welkomstpakket zit
- **Ondertekening:** H-DCN Ledenadministratie

## Technische aanpak

- **Frontend:** Download-knop per lid in de WelcomePackList component (naast "Verzonden" knop)
- **PDF generatie:** jsPDF (al in het project als dependency)
- **Geen backend nodig:** PDF wordt client-side gegenereerd met de member data die al geladen is
- **Template:** Eenvoudige brief-layout met H-DCN logo

## Locatie

- Component: `frontend/src/modules/members/components/WelcomePackList.tsx`
- PDF helper: `frontend/src/utils/generateWelcomeLetter.ts` (nieuw)

## Prioriteit

Laag — kan worden opgepakt na de core membership flow stabiel is.
