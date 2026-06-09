# H-DCN Todo List

# .kiro\specs\code-quality-maintenance
- Add check failing tests (UNit, Integration and e2e) and add test resolution to tasks.md
- Add security analysis (or sperate prompt) to detect 

# Use of google mail vs AWS SES

Presmeet booking form
Booking last row:
Geschat totaal
€822.50

3 deelnemer(s) · 5 feestticket(s) · 5 t-shirt(s) · 2 transfer(s)

Overview omly 2 party tickets (Tickets for meeting attendees, that select attending party, not included)
Feestticket

€199.00

Item	Prijs
Astrid YYYYY	€99.50
Henk YYYY	€99.50

Eindtotaal	€524.00
Totaal betaald	€0.00
Resterend saldo	€524.00


  
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
