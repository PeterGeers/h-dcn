# H-DCN Todo List



## .kiro\specs\code-quality-maintenance
- Add check failing tests (UNit, Integration and e2e) and add test resolution to tasks.md
- Add security analysis (or sperate prompt) to detect 

## Use of google mail vs AWS SES

  
### Enhancer Update Image handler 
Enhance or Remove from scope and just reference practical tools to use 
- Update in line with Enhancer map
- Reference: https://chatgpt.com/s/t_68f8aff529d88191a78e07453be0fdf6


## Multi-language
Extend Multi language (whole app) also in the backend

## Type hints
Voor een AWS Lambda + DynamoDB SaaS-platform zou ik zelf eerder streven naar:

100% type hints op nieuwe code
Verbeter de meest gewijzigde bestanden
Verbeter bestanden met de meeste Pyright/MyPy-waarschuwingen
Laat oude, stabiele code voorlopig met rust



## Standardize naming conventions
Standardize naming conventions to english verbs for tables and fields in dynamo db tables and fix all handlers that touch them. 
This would help reduce errors/ typos as KIRO often assumes the proper names in English

# missing functions
Now about Issue 3: separate price for a variant — that's a feature/design issue rather than a bug introduced by this branch. The variant schema editor doesn't currently support per-variant pricing. That would be a separate feature request. Let me note it but not block on it.


