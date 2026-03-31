# Frontend Hosting Migratie — Tasks

Gebaseerd op de analyse in `refactor.md`.

---

## Fase 1: Voorbereiding (zonder impact op huidige deployment) ✅

- [x] 1.1 `.gitignore` opschonen — verwijder 60+ dubbele `# Added by ggshield` entries
- [x] 1.2 TypeScript type-check toevoegen aan `.git/hooks/pre-commit`
- [x] 1.3 Fix `OAuthCallback.tsx` — vervang hardcoded `de1irtdutlxqu.cloudfront.net` URL-replace door `window.location.origin`
- [x] 1.4 Centraliseer API URLs in frontend — alle componenten die direct `process.env.REACT_APP_API_BASE_URL || 'https://...'` gebruiken laten gaan via `ApiService` of `API_CONFIG`
- [x] 1.5 Controleer welke API URL correct is (`i3if973sp5` prod vs `qsdq51d2r3` dev) en maak consistent
- [x] 1.6 Maak centraal config bestand `scripts/config.sh` met AWS resource IDs voor scripts/tests

## Fase 2: React app voorbereiden voor GitHub Pages

- [x] 2.1 Voeg `"homepage": "/h-dcn/"` toe aan `frontend/package.json`
- [x] 2.2 Update React Router met `basename="/h-dcn"` in `BrowserRouter`
- [x] 2.3 Maak `frontend/public/404.html` met SPA redirect script (redirect naar `index.html` met path als query param)
- [x] 2.4 Voeg redirect-afhandeling toe in `index.html` (parse query param en herstel originele URL)
- [x] 2.5 Test lokaal dat de app correct werkt met base path (`npm start`)

## Fase 3: GitHub Pages activeren en workflow aanpassen

- [x] 3.1 Activeer GitHub Pages in repository settings (source: GitHub Actions)
- [x] 3.2 Pas `.github/workflows/deploy-frontend.yml` aan:
  - Verwijder AWS OIDC credentials stap
  - Verwijder S3 sync en CloudFront invalidatie
  - Voeg `actions/upload-pages-artifact` en `actions/deploy-pages` toe
  - Voeg stap toe om `index.html` te kopiëren naar `404.html` in build output
- [x] 3.3 Voeg `ggshield secret scan ci` stap toe (behouden uit vorige workflow)
- [-] 3.4 Push naar main en verifieer dat GitHub Pages deploy werkt

## Fase 4: Backend configuratie updaten

- [ ] 4.1 Update API Gateway CORS — voeg `https://petergeers.github.io` toe als allowed origin
- [ ] 4.2 Update Cognito User Pool Client callback URLs:
  - Toevoegen: `https://petergeers.github.io/h-dcn/auth/callback`
  - Behouden: `http://localhost:3000/auth/callback`
  - Behouden (tijdelijk): `https://de1irtdutlxqu.cloudfront.net/auth/callback`
- [ ] 4.3 Update Cognito User Pool Client logout URLs:
  - Toevoegen: `https://petergeers.github.io/h-dcn/auth/logout`

## Fase 5: Validatie

- [ ] 5.1 Verifieer dat de app laadt op `https://petergeers.github.io/h-dcn/`
- [ ] 5.2 Test SPA routing — navigeer naar subpagina's en refresh de browser
- [ ] 5.3 Test Google login + OAuth callback flow
- [ ] 5.4 Test Mijn Gegevens pagina (API calls naar backend)
- [ ] 5.5 Test webshop / cart operaties (CORS)
- [ ] 5.6 Smoke tests aanpassen voor nieuwe URL en draaien

## Fase 6: AWS resources opschonen

- [ ] 6.1 Leeg S3 bucket `testportal-h-dcn-frontend`
- [ ] 6.2 Verwijder CloudFront distributie `E2QTMDOE6H0R87`
- [ ] 6.3 Verwijder S3 bucket `testportal-h-dcn-frontend`
- [ ] 6.4 Verwijder IAM role `github-actions-frontend-deploy`
- [ ] 6.5 Verwijder OIDC identity provider (als niet meer nodig voor backend)
- [ ] 6.6 Verwijder GitHub Secrets die niet meer nodig zijn (`AWS_ROLE_ARN`, `CLOUDFRONT_DISTRIBUTION_ID`)

## Fase 7: Opschonen codebase

- [ ] 7.1 Markeer PowerShell deploy scripts als deprecated (comment bovenaan)
- [ ] 7.2 Update `scripts/deployment/README.md` met GitHub Pages instructies
- [ ] 7.3 Update `scripts/config.sh` — verwijder CloudFront/S3 referenties, voeg GitHub Pages URL toe
- [ ] 7.4 Verplaats hardcoded URLs in test scripts naar `scripts/config.sh`
- [ ] 7.5 Update smoke tests met nieuwe GitHub Pages URL
- [ ] 7.6 Verwijder oude CloudFront callback URL uit Cognito (na transitieperiode)
