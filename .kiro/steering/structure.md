---
inclusion: manual
---

# H-DCN Dasd Project Structure

## Root Level Organization

```
h-dcn/
├── frontend/           # React TypeScript application
├── backend/ AWS SAM serverless backend
├── git/  # Git automation scripts
├──ripts/ Deployment and utility scripts
├── Prompts/Documentation and requirements
└── startUpload/       # S3 deployment utilities
```

## Frontend Structure (`frontend/`)

````
frontend/
├── src/
│   ├── components/le UI components
│   ├── modules/based modu
cenarios sd-to-endfor en` est//t `frontendiles int fE2E**: Tess
- **gration testand inteith unit directory w`tests/` rate **: Sepa**Backends
- ntomponeongside cts al: Jest tes*Frontend**ucture
- *ting Stres
## Trformance
mand for peed on-dets load Componenloading**:
- **Lazy iesncpendee demoduloss-oot for crm `src/` rromports**: Flute iAbsoes
- **filule same-mod For ts**:porlative imerns
- **Reattport P

## Imnt settings deploymeorarameters fmplate p*: SAM teastructure*fr*Inion
- *nfigurat cor dynamicore fometer St ParaWSkend**: A**Bacfiles
- nv` bles in `.eria vanvironment EFrontend**:nt
- **metion ManageConfiguratems

###  specific ity/{id}` forions, `/entir collecty` fo`/entit: RLs**ESTful U)
- **Rtscts, evendupro(members, ties  entisinessouped by bused**: Gr**Entity-ba- ern
 pattleteate/de/read/updteea cr: Standards**D OperationCRUre
- **PI Structu
### Are pages
tu for feae}/`featurmodules/{c/sres, `/r main pagfoages/` : `/src/p*Pages** *ents/`
-}/componreatus/{femodule**: `/src/ componentsFeaturents/`
- **ne`/src/componts**: oneomped c
- **SharionganizatComponent Or### s1`)

d.p-uploagit(`s for utilitie-case  kebabripts**:- **Sc`)
ber/em`create_mhandlers (case for : snake_Backend**)
- **d.tsx`Carts (`Member componenlCase ford**: Pascaontenming
- **Frile Na# F##
nventions
# Key Co

#rker
```kage mapac# Python _.py        it_ __in
└──iesdencn depen Pytho  #txt  ts. requiremenlogic
├──in handler      # Ma        .py ─ apptity}/
├─ation}_{enndler/{oper``
hacture:
` strullows this fobda function
Each Lamd Handlers# Backen```

##oint
try pule enMain mode.tsx    # ageature}Pes
└── {Fodule pag  # M        es/     paglities
├── eature uti       # F        tils/─ uc
├─ logi business# API and          ices/  s
├── servomponente-specific ctur# Fea           ts/mponen── coure}/
├les/{featodu`
mcture:
``is struws thlole folh moduEaces
ontend Modul

### Frtternson Pazatie Organi# Modul
#

```latetempe astructur  # SAM infr      late.yaml ─ temp tools
└─Migration          #  Migratie/  ipts
├── scr # Utility     ts/        scrip
├── testsgration       # Inten/tegratio
│   └── inestsUnit t    #      it/     ├── un  sts/
│── teon
├ministratiognito admin/  # C_cognito_ad─ hdcnions
│   └─elete operat      # D/   ─ delete_*
│   ├─perationsdate o# Up*/         e_── updat
│   ├perations  # Read o       get_*/       ├──rations
│ Create ope  #*/       reate_ ├── c
│  ctions)fun(51 s  handler function# Lambda          ler/
├── hand`
backend/
```backend/`)ure (ckend Struct
## Ba```
lities
ti and ules fist     # Te          ── test/   output
└ild n bu# Productio           ld/      ├── buitic assets
   # Sta            ├── public/ files
uration # Config           ig/ ─ conf
│   └─tions type definiypeScript       # T     / ├── typesices
│   nd servutilities aShared     # ls/         ─ utis
│   ├─pagetion caain appli      # Mes/          ├── pagnality
│ce functiocommer   # E-webshop/     └──    │  gement
│manaduct  # Prooducts/     │   ├── pr
│   nistrationember admi      # Mmembers/  │   ├── nt
│  management ve       # E── events/   │   ├│ les
````
