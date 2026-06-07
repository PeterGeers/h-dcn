# H-DCN Todo List
## Presmeet v3 
A few items 
 1. Create a pdf of the booking overview ad payment instrruction if not paid that can be downloaded by the user 
 2. In the overview the cost of the parties are missing for meeting attendants
 2.2 The order details are missing from the overview
 3. The start page of the presmeet when Not having an account should have a search button to find club 
 4. The start page should have the presmeet logo and fh-dce logo as start that starts rather big and size down to small logos at the top 
 5. Betaling registreren Fout bij registreren Request failed with status code 500
 6. Berekening en behandeling van bestellingen klopt niet.
 6.1 Bij orders in presmeet modal the party tickets of delegates are not included
 6.2 Pickup oe drop off is only taken 1 (Even if 4 is asked)
 6.3 Party ticket without name / guest
 6.4 Generate pdf missing (alternative Ctrrl P makes a nice hardcopu)
 6.4.1 Missing club name
 6.4.2 Party tickets for delegates missing in the overview and calculation
 6.5 The order created in the presmeet modal is not shown in the cart
 6.6 Order presmeet products via webshop checkout place iorder installHook.js:1 API request failed: TypeError: Failed to fetch
    at s.request (main.fcdc86ab.js:2:388950)
    at async onClick (531.8e129152.chunk.js:1:35271)
    This order seems not added to the order table
  6.6.1 Order via webshop of some presmeet products
  installHook.js:1 TypeError: t.find is not a function
    at 531.8e129152.chunk.js:1:6804
    at 531.8e129152.chunk.js:1:6891
    at Object.Ha [as useMemo] (main.fcdc86ab.js:2:255378)
    at main.fcdc86ab.js:2:171532
    at ne (531.8e129152.chunk.js:1:6704)
    at ma (main.fcdc86ab.js:2:250969)
    at Cs (main.fcdc86ab.js:2:265191)
    at Sl (main.fcdc86ab.js:2:311450)
    at yc (main.fcdc86ab.js:2:299675)
    at mc (main.fcdc86ab.js:2:299603)


7. Migrate presmeet products to new model. Make sure the presmeet modal keeps working with the new presmeet product datamodel
8. Presidents'Meeting Booking
8.1 >> Overzicht Party tickets for delegates are missing
8.2  >>Admin Data is white on white and not in line with the standard presentation dwefinition 
9. Product modal in webshopbeheer
9.1 Variant schema white on white
9.2 Aankoopregels white on white
9.3 Aankoopregels lijkt een dropdown (met hard coded comtent) maar heeft geen opties
10. Evenementenadmin istratie webmaster@h-dcn.nl heeft geen rechten (Evenementen Events_Read Evenementen - Inzage in alle evenementen Events_Export Evenementen - Export van evenementengegevens Events_CRUD Evenementen - Volledig beheer van evenementen)

# .kiro\specs\code-quality-maintenance
- Add check failing tests (UNit, Integration and e2e) and add test resolution to tasks.md
- Add security analysis (or sperate prompt) to detect 

# Use of google mail vs AWS SES

# Test steering
The key is to use react-scripts test not npx jest directly. Now let me run the actual failing test  should we add a remark in .kiro\steering\testing.md



# Prepare for demo
##  different functions by user type,
-- different user screen by member type
-- Toegang tot platform afhankelijk van toegangscontrole
--- Leden zien alleen eigen gegevens en clubsjop
--- Bestuursleden met een h-dcn mail account hebben toegang afhankelijk van hun rol
--- Regio leden alleen toegang to regio specifieke gegevens (vaak alleen leesrechten)
--- AB leden toegang tot alle gegevens (Vaak alleen leesrechten)
--- ledenadministratie@h-dcn.nl lees-en schrijfrechten op de ledenadministratie
--- webmaster@h-dcn.nl lees- en schrijfrechten op het hele systeem
--- secretaris@h-dcn.nl
--- penningmeester@h-dcn.nl
--- Regio secretarissen regio evenementen al dan niet met budget en actuals

## webshop and payment
--- Productbeheer (met fotos, maten, ..)
--- Webshop met Producten en Orders (status= Winkelwagen, Besteld, Betaald, Verzonden)
--- Betaalsysteem Stripe of Tikkies??

## Evenementen administratie,
--- lijst van evenementen met posters (if available)
--- Evenementen kalender (voor op website, facebook, clubblad)
--- Manage evenement budget en actuals voor specifieke h-dcn evenemnten

## Ledenadministratie
--- Administratie van leden, gezinsleden, sponsors, adverteerders, etc..
--- Leden++ kunnen zelf persoonsgegevens aanpassen
--- Alleen leden++ hebben toeganmg tot clubsjop
--- Nieuwe mensen kunnen zich aanmelden (invullen basis gegevens)
---- Proces flow op basis van status (aangemeld, regio akkoord, ledenadministratie akkoord, lid++)
--- Automatische generatie van ALV oorkondes, Brieven(e-mails) nieuwe aanmeldingen, 
--- AI modus mbt Ledenadministratie. Vragen jn natuurlijke taal hoeveel gezinsleden per regio en het totaal etc... ... 

## Opties
- Ondersteuning financiele administratie
- Eigen webshop per regio met regio gesloten , H-DCN gsloten of oopenbaar
- Uitbreidbaar naar andere federatie clubs



--

## 💰 Factuurinboekingen en Onkostendeclaraties

### Core Functionaliteit
- **Upload Facturen** en onkosten declaraties bijlage (Google Drive voor gratis storage)
- **Genereer boekingen** met relevante bedragen:
  - Totaal en BTW
  - Koppelingen met ingevoerde bijlagen
  - Relevante attributen voor financiële administratie
  - [Optioneel] Betalingsbestanden voor ING Bank automatische betalingen

### Toegangsrechten
- **Ingvoerders:** Kunnen eigen facturen/declaraties raadplegen
- **Penningmeester:** Kan alle gegevens raadplegen
- **FinAdmin groep:**
  - Volledige toegang tot raadplegen en muteren
  - Opdracht verstrekken voor boekings- en betalingsbestanden
  - Status definitief zetten
- **FinOnkosten groep:**
  - Invoeren en raadplegen van specifieke declaraties
  - Muteren alleen zolang boekingen niet definitief zijn

### Technische Eisen
- **Data integriteit:** Geen wijzigingen na definitieve boekingen
- **UI/UX:** Zelfde Look & Feel als andere modules
- **Responsive:** Telefoonvriendelijke interface

---

## 🔧 Technische Updates

### Enhancer Update
- Update in line with Enhancer map
- Reference: https://chatgpt.com/s/t_68f8aff529d88191a78e07453be0fdf6

### Security Improvements
**Code review bevindingen - medium/low severity issues geadresseerd:**

**Voor productie deployment:**
- Content Security Policy (CSP) toevoegen
- Proper input validation op backend implementeren
- Dedicated sanitization library (DOMPurify) gebruiken
- Reguliere security audits en dependency updates

**Status:** Kritieke security vulnerabilities opgelost, functionaliteit behouden, XSS bescherming verbeterd
