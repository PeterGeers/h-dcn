

# H-DCN Todo List

- Prepare for demo
-- different functions by user type,
-- different user screen by member type
-- Toegang tot platform afhankelijk van toegangscontrole
--- Leden zien alleen eigen gegevens en clubsjop
--- Bestuursleden met een h-dcn mail account hebben toegang afhankelijk van hun rol
--- Regio leden alleen toegang to regio specifieke gegevens (vaak alleen leesrechten)
--- AB lden toegang tot alle gegevens (Vaak alleen leesrechten)
--- ledenadministratie@h-dcn.nl lees-en schrijfrechten op de ledenadministratie
--- webmaster@h-dcn.nl lees- en schrijfrechten op het hele systeem
--- secretaris@h-dcn.nl
--- penningmeester@h-dcn.nl
--- Regio secretarissen regio evenementen al dan niet met budget en actuals

-- webshop and payment
--- Productbeheer (met fotos, maten, ..)
--- Webshop met Producten en Orders (status= Winkelwagen, Besteld, Betaald, Verzonden)
--- Betaalsysteem Stripe of Tikkies??

-- Evenementen administratie,
--- lijst van evenementen met posters (if available)
--- Evenementen kalender (voor op website, facebook, clubblad)
--- Manage evenement budget en actuals voor specifieke h-dcn evenemnten

-- Ledenadministratie
--- Administratie van leden, gezinsleden, sponsors, adverteerders, etc..
--- Leden++ kunnen zelf persoonsgegevens aanpassen
--- Alleen leden++ hebben toeganmg tot clubsjop
--- Nieuwe mensen kunnen zich aanmelden (invullen basis gegevens)
---- Proces flow op basis van status (aangemeld, regio akkoord, ledenadministratie akkoord, lid++)
--- Automatische generatie van ALV oorkondes, Brieven(e-mails) nieuwe aanmeldingen, ...




📊 Backend API Consistency Analysis
🎯 Immediate Recommendations:
Implement Missing Endpoints - Complete webshop, payments, orders functionality

Done: Standardize Authentication - Add getAuthHeaders() to all API calls
Done: Centralize API Configuration - Use environment variables consistently
Done: Standardize Error Handling - Create consistent error handling patterns
Done: The inconsistent authentication is the root cause of the 500 errors you're experiencing. Most API calls need the Authorization header added.
---

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
