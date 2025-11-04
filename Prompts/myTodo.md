# H-DCN Todo List

📊 Backend API Consistency Analysis
🎯 Immediate Recommendations:
Done: Standardize Authentication - Add getAuthHeaders() to all API calls
Done: Centralize API Configuration - Use environment variables consistently
Implement Missing Endpoints - Complete webshop, payments, orders functionality
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
