# Frontend Hosting Migratie: AWS (S3 + CloudFront) → GitHub Pages

## Doel

De volledige frontend hosting verplaatsen van AWS (S3 bucket + CloudFront CDN) naar GitHub Pages. Dit elimineert AWS-kosten voor frontend hosting en vereenvoudigt de deployment pipeline.

---

## Huidige situatie

### Infrastructuur (wordt afgebouwd)

- S3 bucket: `testportal-h-dcn-frontend`
- CloudFront distributie: `E2QTMDOE6H0R87`
- Site URL: `https://de1irtdutlxqu.cloudfront.net`
- API URL: `https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev`
- Regio: `eu-west-1`

### Wat al gedaan is (Fase 1-4)

- ✅ `.gitignore` opgeschoond
- ✅ TypeScript type-check in pre-commit hook
- ✅ `OAuthCallback.tsx` hardcoded URL-replace gefixed
- ✅ API URLs gecentraliseerd via `API_CONFIG`
- ✅ OIDC identity provider + IAM role aangemaakt
- ✅ GitHub Secrets en Variables geconfigureerd
- ✅ GitHub Actions workflow (`deploy-frontend.yml`) werkend met S3 deploy
- ✅ `frontend/public/` getracked in git (was geblokkeerd door `.gitignore`)

### Wat verandert

| Aspect  | Oud (AWS)                              | Nieuw (GitHub Pages)                  |
| ------- | -------------------------------------- | ------------------------------------- |
| Hosting | S3 + CloudFront                        | GitHub Pages                          |
| URL     | `https://de1irtdutlxqu.cloudfront.net` | `https://petergeers.github.io/h-dcn/` |
| CDN     | CloudFront                             | GitHub's CDN (Fastly)                 |
| SSL     | AWS Certificate Manager                | Automatisch via GitHub                |
| Deploy  | `aws s3 sync` + CloudFront invalidatie | `actions/deploy-pages`                |
| Kosten  | S3 + CloudFront + Route53              | Gratis                                |
| IAM     | OIDC role nodig                        | Niet nodig                            |

---

## Technische aandachtspunten

### React Router (SPA routing)

GitHub Pages ondersteunt geen server-side redirects. React Router met `BrowserRouter` geeft 404's bij page refresh. Oplossing: een `404.html` die redirected naar `index.html` met de oorspronkelijke URL als query parameter.

### Base path (`/h-dcn/`)

GitHub Pages serveert vanuit `https://petergeers.github.io/h-dcn/`. De React app moet weten dat de base path `/h-dcn/` is:

- `package.json`: `"homepage": "/h-dcn/"`
- React Router: `<BrowserRouter basename="/h-dcn">`
- Alle asset references worden automatisch correct via `%PUBLIC_URL%`

### CORS

De API Gateway CORS configuratie moet de nieuwe GitHub Pages URL toestaan als origin. De huidige CloudFront URL moet ook tijdelijk blijven werken tijdens de transitie.

### Cognito OAuth callbacks

De Cognito User Pool Client callback URLs moeten bijgewerkt worden:

- Toevoegen: `https://petergeers.github.io/h-dcn/auth/callback`
- Behouden (tijdelijk): `https://de1irtdutlxqu.cloudfront.net/auth/callback`
- Behouden: `http://localhost:3000/auth/callback`

### Environment variabelen

`REACT_APP_*` variabelen worden compile-time ingebakken. De GitHub Actions workflow genereert het `.env` bestand uit GitHub Secrets/Variables — dit blijft hetzelfde.

---

## GitHub Actions workflow (aangepast)

De workflow verandert van S3 sync naar GitHub Pages deploy:

1. Checkout code
2. Setup Node.js 18
3. `npm install` in `frontend/`
4. Genereer `.env` uit GitHub Secrets/Variables
5. `npm run build`
6. Kopieer `index.html` naar `404.html` (SPA routing fix)
7. Deploy naar GitHub Pages via `actions/deploy-pages`

### Wat wegvalt

- AWS OIDC credentials configuratie
- `aws s3 sync`
- CloudFront invalidatie
- S3/CloudFront gerelateerde IAM permissions

---

## Opschonen AWS resources (na succesvolle migratie)

Na validatie dat GitHub Pages correct werkt:

1. S3 bucket `testportal-h-dcn-frontend` legen en verwijderen
2. CloudFront distributie `E2QTMDOE6H0R87` disablen en verwijderen
3. IAM role `github-actions-frontend-deploy` verwijderen
4. OIDC identity provider verwijderen (tenzij gebruikt voor backend)
5. ACM certificaat verwijderen (als niet meer nodig)
6. GitHub Secrets opschonen (`AWS_ROLE_ARN`, `CLOUDFRONT_DISTRIBUTION_ID` niet meer nodig)

---

## Risico's en rollback

- **Rollback:** S3 bucket en CloudFront blijven bestaan tot alles gevalideerd is
- **SPA routing:** 404.html workaround is standaard voor GitHub Pages + React
- **Performance:** GitHub Pages CDN (Fastly) is vergelijkbaar met CloudFront
- **Limieten:** GitHub Pages heeft een soft limit van 1GB en 100GB/maand bandwidth — ruim voldoende voor deze app
- **Custom domain:** Kan later toegevoegd worden via GitHub Pages settings + DNS CNAME
