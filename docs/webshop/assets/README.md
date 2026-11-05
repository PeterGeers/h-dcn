# Screenshots voor de webwinkel-handleidingen

Deze map bevat de afbeeldingen (screenshots) die in de webwinkel-handleidingen
worden gebruikt. In de Markdown-bronnen staan op de juiste plekken
**placeholders** met een vaste bestandsnaam. Plaats hier een afbeelding met
exact die naam, render opnieuw, en de screenshot verschijnt in de HTML/PDF.

## Hoe werkt het

In de handleidingen staan placeholders in dit formaat:

```
> 📷 **[Screenshot: korte omschrijving]** — bestand: `assets/winkel-winkelwagen.png`
```

Om een placeholder te vervangen door een echte afbeelding:

1. Maak de screenshot en sla hem op in deze map met de genoemde **bestandsnaam**.
2. Vervang in de `.md` het placeholder-blok door een afbeeldingsverwijzing, bijv.:
   `![Winkelwagen met twee producten](assets/winkel-winkelwagen.png)`
3. Render opnieuw met `node scripts/docs/render-webshop-manuals.mjs`.

> Je kunt de placeholders ook laten staan tot je alle screenshots hebt; ze worden
> dan als herkenbaar grijs kader in de HTML/PDF getoond.

## Aanbevelingen

- **Formaat:** PNG (scherpe UI-tekst). Breedte ± 1200–1600 px is ruim voldoende.
- **Inhoud:** toon alleen het relevante schermdeel; vermijd persoonsgegevens van
  echte leden (gebruik testdata of maak gevoelige gegevens onleesbaar).
- **Taal:** maak de screenshots in de Nederlandse weergave van de portal.

## Verwachte bestandsnamen

### Ledenhandleiding (`handleiding-winkel.md`)

| Bestandsnaam                          | Wat het toont                                      |
| ------------------------------------- | -------------------------------------------------- |
| `winkel-start.png`                    | Webwinkel-startscherm met productoverzicht         |
| `winkel-productoverzicht.png`         | Productoverzicht met meerdere producten            |
| `winkel-productkaart.png`             | Productkaart met variantkeuze (maat/kleur)         |
| `winkel-aankoopregel.png`             | Productkaart met melding over een aankoopregel     |
| `winkel-winkelwagenicoon.png`         | Winkelwagen-icoon met aantal items                 |
| `winkel-winkelwagen.png`              | Winkelwagen met twee producten en totaalbedrag     |
| `winkel-deelnemersgegevens.png`       | Deelnemersgegevens invullen in de winkelwagen      |
| `winkel-afrekenen.png`                | Afrekenscherm (overzicht, leveroptie, afleveradres)|
| `winkel-betaalmethode.png`            | Keuze van betaalmethode (iDEAL/Creditcard/Overschrijving) |
| `winkel-betaling-terugkeer.png`       | Terugkeer na betaling met bevestiging              |
| `winkel-bevestiging.png`              | Bestelbevestiging met bestelnummer en PDF-knop     |
| `winkel-mijn-bestellingen.png`        | Mijn bestellingen met status en track & trace      |
| `winkel-foutmelding.png`              | Voorbeeld van een foutmelding bij afrekenen        |

### Beheerdershandleiding (`handleiding-beheer.md`)

| Bestandsnaam                          | Wat het toont                                      |
| ------------------------------------- | -------------------------------------------------- |
| `beheer-overzicht.png`                | Webshop Beheer met de vier tabbladen               |
| `beheer-producten-lijst.png`          | Productlijst met groep/subgroep-filter             |
| `beheer-product-bewerken.png`         | Product bewerken                                   |
| `beheer-bulk-varianten.png`           | Bulk-varianten aanmaken                            |
| `beheer-voorraad.png`                 | Voorraad toevoegen                                 |
| `beheer-bestellingen-tabel.png`       | Bestellingen-tabel met filters en sortering        |
| `beheer-orderdetail.png`              | Orderdetails met statusovergangen                  |
| `beheer-batch-acties.png`             | Batch-acties met geselecteerde bestellingen        |
| `beheer-betalingen-totalen.png`       | Betalingen met totaalkaarten                       |
| `beheer-betaling-registreren.png`     | Betaling registreren in het detailscherm           |
| `beheer-rapporten.png`                | Rapporten met type-keuze en export                 |
| `beheer-picklist.png`                 | Pick-list van een event (betaald/klaar/uitgereikt) |
