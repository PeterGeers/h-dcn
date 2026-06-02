In the .kiro\specs\presmeet\wireframe  there is a description of a solution that in the base sells itenms for an event (The PresMeet)
- tickets for a meeting
- tickets for a party
- airport pickup
- airport drop off
- hotel rooms
- t-shirts (male and female with different sizes)

The clients base are clubs associated to the fh-dce (h-dcn is just such a club)

The idea is to implement this in the h-dcn project 
- using the webshop with extended logic to handle item specifics
- using authentication flow logging users to a predefined list of ca. 65 clubs
- Allowing these users to shop in the webshop and note all relevant information to their order
- Reporting status of what is in orders and carts to see what is already ordered and what is planned
- Payment via Mollie or direct payment with an option to update the status to paid

What about all orderabble items are products. Atttributes can be product type driven attrributes in json like role, name, pickup, etc..

I thinktourist tax is an item not needed abnd should be included in the hotel price and probably hotel rooms will be out of scope.

## Status notes 
Confirmed — none of the 20 remaining failures are PresMeet-related. They are all pre-existing issues in:

Integration tests (API Gateway, auth performance, member reporting) — these require live AWS infrastructure
test_get_members_filtered — a pre-existing unit test for a different handler
test_passkey_bug_condition — from a different spec