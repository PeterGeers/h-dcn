Factuurinboekingen en Onkostendeclaraties
** Upload Facturen en onkosten declaraties bijlage  (f.e.  Google Drive omdat we daar veel gratis storage hebben)
** Genereer een boeking met de relevante bedragen 
*** Zoals Totaal en BTW
*** Koppelingen met de ingevoerd bijlagen (Koppelingen naar de geimporteerde documenten)
*** Voeg relevante attributen toe om de gegegvens op een correcte manier in de financiële administratie te kunnen laden 
*** [Indien niet in de FinAdmin] Genereer betalingen die ingeladen kunnen worden bij de ING Bank voor automatische betalingen
*** Ingvoerde gegevens kunnen geraadpleegd worden door de penningmeester en de persoon die een specifieke factuur of declaratie heeft ingevoerd
*** Gegevens kunnen niet meer gewijzigd worden als er boekingen zijn gegenereerd voor de financiële administratie
*** groep FinAdmin: Toegan voor alles raadplegen en muteren (Ook het status veld). Opdracht verstrekken voor aanmaken boekingsbestand en betalings bestand(Hierbij wortdt het status bestand op definitief gezet).  
*** groep FinOnkosten Voor in invoeren en raadplegen van specifieke declaraties en facturen. Muteren kan alleen zolang de boekingen nog niet definitief zijn
*** Gebaseerd op dezelfde Look en Feel als de andere modules met ook een telefoon vriendelijke interface














** The code review found many more medium and low severity issues. The most critical security vulnerabilities have been addressed. For production deployment, consider:
Adding a Content Security Policy (CSP)
Implementing proper input validation on the backend
Using a dedicated sanitization library like DOMPurify
Regular security audits and dependency updates
The fixes maintain functionality while significantly improving security posture against XSS attacks and credential exposure.
