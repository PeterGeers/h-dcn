En in de "Event Creation Workflow" sectie bij "Regels":

Duplicaat-check moet vanuit de admin UI werken (frontend waarschuwing bij vergelijkbare naam+datum)

Dus bij handmatige invoer via de admin UI:

Gebruiker vult naam + datum + locatie in
Bij submit (of on-blur): backend check via ?check_duplicates=true
Bij match: frontend toont waarschuwing "Er bestaat al een vergelijkbaar event" + laat het bestaande event zien