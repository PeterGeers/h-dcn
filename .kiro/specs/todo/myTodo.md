# H-DCN Todo List

Here's what you need to do in your DNS provider to validate the certificate:

# Findings order pipeline improvements 
- user peter@pgeers.nl
## Order confirmation
- Nice new Betaling succesvol! Bestelling wordt verwerkt... Bestelnummer H-260610-001  Wordt daarna niet gebruikt en wordt ook niet opgehoogd bij nieuwe bestelling
- Order confirmation online Ordernummer: 
4a920804-1ce7-4a9d-ab64-16e16dd4f30a
- Order confirmation Download PDF  different layout, missing all client attrributes for Invoice adress and delivery address and Cliet and the UUID as ordernumber that are visible in the online variant. Why not download the online one
- Status: beyaald (should be not paid or waiting payment) in both online and downloaded
## Winkelwagen
- When i arrive in cart it should list all previous orders with their status as per last design from user and then create a new empty order

# presidents meeting
- No access Fout bij laden PresMeet Network Error
- Network tab Request URL
https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod/presmeet/orders?event_id=evt-pm2027
Request Method
OPTIONS
Status Code
403 Forbidden
Remote Address
3.173.161.59:443
Referrer Policy
strict-origin-when-cross-origin

- Network tab Request URL
https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod/presmeet/orders?event_id=evt-pm2027
Referrer Policy
strict-origin-when-cross-origin
Event_id is probably wrong.

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