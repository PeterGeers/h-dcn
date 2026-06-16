## Update testportal

Please deploy the updates in the feature  feature/generic-event-booking and deploy it with the workflows frontend and backend with mode = test to deploy it as a new version in testportal.h-dcn.nl

# (https://testportal.h-dcn.nl/webshop_management)

Saving a record with existing rules gets message validation failed. I cannot copt the text in the rsponse and no message in the console but it starts referring to order_item_fields[0].validation.min-length nust be between 1 and 1000 in the rcord is 1 and 100
Wondering where fields[9] refers to  same message for max lengtn
Then similar messages for "field":"purvghase....". "message": "max_per_member must be an integer"i have filled a 1 and a 5 for max per member and per order



In webshop beheer The filter for events is not a dropdown filter But a statis list which takes a lot of spece. It does not comply with ui standards (drop down is white on white)

The Variant Scheme, Bestelvelden and aankoop regels have a nice colapseble window. I do not know what the default way is or if there is one. If we want to use this as standard when having multiple sub modals in a modal we have to add it to the ui steering as standard and have to add Afbeeldingen and events to it

The webshop (algemeen) event is shown double but select and deselect works on both. STRANGE

Product variants Individuele variant toevoegen/verwijderen
Selecteer een waarde per as om een specifieke variant te beheren. You can select one to delete. It says removed but irt remains in it. Adding attributes to a variants like price, oversell, .. is not prossible

There is no label showing the variants as a json string in a field. There is nos upport for the Uop and Down way management of variants. At this moment you have to manually create each variant adding a label. 

There is no support for a logic sort of cloth measures XS, S, M, L, ... Is there a standard way of definition and sorting of cloth sizes

# https://testportal.h-dcn.nl/webshop

The sorting of sizes does not work

Many products cannot be ordered as they seem not available. The stock and oversell ioptions  can not be edited at this moment in product managemenmt

When adding an item to the cart and paying it by overwriting i get this message:  Failed to resolve member record  (No console message). I am logged in and have a member record. I have not a Lidnummer.

# If I open https://testportal.h-dcn.nl/events/test-event-rally-2027/booking
An empty window appears and console says
installHook.js:1 TypeError: Cannot read properties of undefined (reading 'map')
    at P (293.5bffb72b.chunk.js:1:8368)
    at ma (main.7e6d2b6f.js:2:266048)
    at Sl (main.7e6d2b6f.js:2:325646)
    at yc (main.7e6d2b6f.js:2:314754)
    at mc (main.7e6d2b6f.js:2:314682)
    at gc (main.7e6d2b6f.js:2:314545)
    at oc (main.7e6d2b6f.js:2:311325)
    at rc (main.7e6d2b6f.js:2:309876)
    at S (main.7e6d2b6f.js:2:164747)
    at MessagePort.R (main.7e6d2b6f.js:2:165281)

main.7e6d2b6f.js:2 Uncaught TypeError: Cannot read properties of undefined (reading 'map')
    at P (293.5bffb72b.chunk.js:1:8368)
    at ma (main.7e6d2b6f.js:2:266048)
    at Sl (main.7e6d2b6f.js:2:325646)
    at yc (main.7e6d2b6f.js:2:314754)
    at mc (main.7e6d2b6f.js:2:314682)
    at gc (main.7e6d2b6f.js:2:314545)
    at oc (main.7e6d2b6f.js:2:311325)
    at rc (main.7e6d2b6f.js:2:309876)
    at S (main.7e6d2b6f.js:2:164747)
    at MessagePort.R (main.7e6d2b6f.js:2:165281)


# In https://testportal.h-dcn.nl/events/test-event-presmeet-2027/booking

I see Presidents Meeting 2027. 📅 1 juni 2027 – 3 juni 2027,  319 days until registration close
I see an empty leght blue box wit 3 times max .... per club
Then I can add a name and a role
Select add product But no product is shown. 
Maybe this functrion is not e real event

I can add a second person??

The best logic is to show the event and list the products that can be ordered in the specific event.
Depending on the product there is a requirement for a name, role or anaything else. Based on the product rules there is a requirement for some products by order like  Minimal 1 by order


# https://testportal.h-dcn.nl/events
    Saving an updated event is not possible 

Fout bij opslaan evenement, Serverfout - probeer het later opnieuw

installHook.js:1 Fout bij opslaan evenement: {status: 500, message: 'Serverfout - probeer het later opnieuw', details: '{"error": "Internal server



Yes, there's one issue. Looking at the steering rules:

Moto (mock_aws) usage — Always load the handler inside the mock_aws() context so boto3 resources created during handler execution are intercepted

The property tests create the mock_aws() context inside each test invocation (inside the @given decorated function), which means:

Tables are created ✓
Handler is loaded inside mock context ✓
Auth is patched via patch.multiple('app', ...) ✓
importlib pattern is used (no sys.path manipulation) ✓
Environment variables set before import ✓