# GitGuardian Quota Fix — Prompt voor andere projecten

## Context

Het GitGuardian free plan (10.000 API calls/maand, gedeeld over alle projecten) raakte uitgeput door:

- Dubbele scanning: lokale Kiro hook + CI ggshield-action bij elke deploy
- CI `fetch-depth: 0` zorgde voor full-history scans (~30 calls per deploy)
- Hoog deploy-volume door Kiro-automatisering (~270 deploys/maand)

Oplossing toegepast in h-dcn (juni 2026): lokale fallback scanner + CI scan verwijderd.

## Prompt (kopieer naar een Kiro sessie in het andere project)

```
Ik wil het GitGuardian quota-probleem fixen in dit project. Het probleem:
- Mijn GitGuardian free plan heeft 10.000 API calls/maand (gedeeld over alle projecten)
- Het quota is op door dubbele scanning (lokaal + CI) en fetch-depth:0 in CI
- Ik wil dezelfde fix als in h-dcn toepassen

Doe het volgende:

1. Kopieer `scripts/scan-secrets-local.ps1` van h-dcn naar dit project (of maak een equivalente lokale secret scanner):
   - Pure regex, geen API calls, werkt offline
   - Detecteert: AWS keys, private keys, Stripe, GitHub/GitLab tokens, Google API keys, Slack tokens, generic secret assignments, connection strings, JWT tokens
   - Respecteert ignored paths (test files, locales, node_modules, .venv, lock files)
   - Exit code 1 bij secrets, 0 als clean
   - Slaat regels over met "example", "placeholder", "dummy", "mock", "fake"
   - Slaat environment variable references over (${ }, process.env, os.environ)

2. Update de Kiro preToolUse hook (.kiro/hooks/ggshield-pre-commit.kiro.hook):
   - Probeer eerst ggshield (API-based)
   - Als quota/rate-limit error: fallback naar lokale scanner
   - Blokkeer altijd bij gevonden secrets, ongeacht welke scanner
   - Version: "3"

3. Verwijder ggshield uit de CI/CD workflows (GitHub Actions):
   - Commentarieer de ggshield-action stap uit (niet deleten)
   - Voeg een NOTE comment toe met uitleg wanneer het teruggezet moet worden:
     "Re-enable if multiple developers push without Kiro, or if quota is upgraded"
   - Verwijder ook fetch-depth: 0 (niet meer nodig zonder ggshield)

4. Als er een .gitguardian.yaml bestaat, laat die staan (wordt nog door lokale ggshield gebruikt)

Het resultaat moet zijn:
- Geen CI API calls meer naar GitGuardian
- Lokale hook scant nog steeds bij elke commit via Kiro
- Bij quota-uitputting werkt de lokale fallback scanner (geen API nodig)
- Commits worden geblokkeerd bij gevonden secrets
```

## Referentie-implementatie (h-dcn)

| Bestand                                     | Functie                                  |
| ------------------------------------------- | ---------------------------------------- |
| `scripts/scan-secrets-local.ps1`            | Lokale regex scanner (fallback)          |
| `.kiro/hooks/ggshield-pre-commit.kiro.hook` | Kiro hook v3 (ggshield + fallback)       |
| `.github/workflows/deploy-frontend.yml`     | CI scan uitgecommentarieerd              |
| `.github/workflows/deploy-backend.yml`      | CI scan uitgecommentarieerd              |
| `.gitguardian.yaml`                         | Ignored paths configuratie (ongewijzigd) |

## Wanneer CI scan terugzetten

- Meerdere developers pushen zonder Kiro
- GitGuardian upgrade naar Teams plan (100k calls/maand)
- Service account key met apart quota geconfigureerd
