
# Feature: 
Spec to merge with main incl all necessary dynamodb migration scripts.See previous actions .kiro\specs\Common\merge-to-main Rel1

# Feature: 
possibility to update club name  in the order file (what is the impect in the S3 file)


# Root Cause Analysis: 
While I do not understand when there are two AXIS THAT THERE IS NOT A VARIANT RECORD FOR each combination of variant1 and variant 2. This is an issue we can temporary limit to one axis. Now we have to work with a linmit of 1 axis See file [text](<RCA variants BookingForm.md>)

## Scrollable modals in event calendar iframe in google site
Replace the modal with an inline expandable card Instead of a modal overlay, expand the event details inline (below or replacing the card) within the page flow. Since it's part of the normal document flow, iframe scrolling works naturally. No overlay, no scroll conflict.

## Evenementen calendar Locatie
Recommendation for H-DCN:  Clickable to open google maps/ Or open a google maps view
The simplest approach: just make the location text field clickable with a Google Maps search URL. No coords needed, and it handles addresses, venue names, and city names gracefully.
Recommendation for H-DCN
Given your stack (Chakra UI, events module), the lightest approach:
Wrap the event location text in a Link with https://www.google.com/maps/search/?api=1&query={encoded}
Add a small map pin icon
Use isExternal so it opens in a new tab
No API keys needed, no extra dependencies, works on all platforms. If an admin pastes a specific Google Maps or Apple Maps URL into a location_url field, prefer that over the auto-generated search link.

## myorders.tsc wiring