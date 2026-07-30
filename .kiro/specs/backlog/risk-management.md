# Risk Management: Credential Exposure op Developer Laptops

## Context

Repo- en CI-scanning (GitGuardian) vangt secrets op die in git terechtkomen. Maar credentials die **lokaal op de laptop** staan — `.env` bestanden, shell history, MCP configs, AI-gegenereerde artefacten — worden niet door repo-scanning gezien. Bij een gestolen/gecompromitteerd laptop zijn die direct bruikbaar.

## Huidige maatregelen (✅ in orde)

- GitGuardian pre-commit hook (lokale regex scan)
- GitGuardian pre-push hook (API scan)
- `.secrets`, `.env`, credential-bestanden in `.gitignore`
- MCP configs bevatten geen secrets (alleen `uvx` commands)
- Kiro pre-commit hook als extra vangnet

## Risico's en aanbevelingen

### 1. Statische AWS credentials → Migreer naar AWS SSO/Identity Center

| Item                | Huidig                                                    | Gewenst                                       |
| ------------------- | --------------------------------------------------------- | --------------------------------------------- |
| AWS auth            | Statische keys in `~/.aws/credentials` (nonprofit-deploy) | AWS SSO session tokens (verlopen na 1-12 uur) |
| Impact bij diefstal | Keys onbeperkt geldig tot handmatige rotatie              | Token verlopen automatisch                    |

**Actie:** Configureer AWS IAM Identity Center, maak een permission set voor deploy, vervang `--profile nonprofit-deploy` door SSO-based profile.

### 2. Google Service Account Key → Workload Identity Federation

| Item        | Huidig                                                  | Gewenst                                      |
| ----------- | ------------------------------------------------------- | -------------------------------------------- |
| Google auth | `.googleCredentials.json` (service account key op disk) | Workload Identity Federation (geen key file) |
| Alternatief | Als WIF niet mogelijk: roteer key elk kwartaal          |                                              |

**Actie:** Onderzoek of de gspread/Google Sheets integratie via WIF kan draaien. Zo niet, stel kwartaal-rotatie in.

### 3. Shell history bevat mogelijk secrets

PowerShell slaat alle commando's op in:

```
(Get-PSReadLineOption).HistorySavePath
```

Als ooit een token of key in de terminal is geplakt, staat die daar permanent.

**Actie:** Voeg een periodieke scan toe of clear gevoelige entries. Overweeg `Set-PSReadLineOption -HistorySaveStyle SaveIncrementally` met een cleanup script.

### 4. Endpoint scanning (lokale bestanden buiten git)

GitGuardian kan ook niet-git-tracked bestanden scannen:

```bash
ggshield secret scan path . --recursive
```

Dit vangt credentials op in `.env`, downloads, config dirs, etc.

**Actie:** Voeg een `userTriggered` Kiro hook toe of een scheduled task die periodiek draait.

### 5. Credential rotatie policy

| Credential                 | Rotatie-interval          | Verantwoordelijke |
| -------------------------- | ------------------------- | ----------------- |
| AWS static keys            | → elimineren via SSO      | Peter             |
| Google service account key | Kwartaal (tot WIF)        | Peter             |
| Stripe API keys            | Jaarlijks of bij incident | Peter             |
| Cognito app client secret  | N.v.t. (public client)    | —                 |

## Prioriteit

1. **Hoog** — AWS SSO migratie (elimineert het grootste risico)
2. **Middel** — Google key rotatie / WIF onderzoek
3. **Laag** — Shell history scanning, endpoint scan hook

## Referenties

- GitGuardian webinar "Every laptop is a credential store" (22 juli 2026)
- [AWS IAM Identity Center docs](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
- [Google Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
