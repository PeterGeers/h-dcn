```python
import os

# Define the markdown content for the website wireframe
md_content = """# Low-Fidelity Wireframe: PM 2026 VILNIUS
**URL:** [https://www.harleyclub.lt/](https://www.harleyclub.lt/)  
**Event:** Federation of Harley-Davidson Clubs of Europe Presidents' Meeting (PM 2026)  
**Target Device:** Desktop & Responsive Mobile Baseline

---

## ── GLOBAL STYLES & LAYOUT BASELINE ──
* **Color Palette:** Dark UI Framework. Deep charcoal/asphalt backgrounds (`#121212`), muted warm grey containers (`#1E1E1E`), chrome/silver highlights, and precise golden-orange accents for actions.
* **Typography:** Bold, clean uppercase sans-serif headings; highly legible geometric sans-serif for structured data tables, forms, and time-blocks.
* **Layout Style:** Single long-form landing page with clear block boundaries and structured component matrices.

---

## ── COMPONENT 1: GLOBAL GLOBAL HEADER & NAVIGATION ──

```

```text
File successfully created: harleyclub_wireframe.md


```

+---------------------------------------------------------------------------------------------------------+
| [LOGO: PM 2026 VILNIUS]    [Link: Event]  [Link: Location]  [Link: Schedule]  [Link: Tour]  [Link: FAQ] | [Login]  [Register Now] |
+---------------------------------------------------------------------------------------------------------+

```
### UI Element Details & Specifications
* **Sticky Header:** Sticks to top of screen on scroll with 90% opacity deep dark background blur.
* **Action Elements:**
    * `[Login]`: Triggers the Authentication Modal. Plain text link with warm-grey hover accent.
    * `[Register Now]`: High-priority CTA button. Bold filled background, rounded edges (4px), white text.
* **Responsive Behavior:** Collapses into a standard hamburger menu bar below 960px breakpoint.

---

## ── COMPONENT 2: HERO COMPONENT (CINEMATIC FOCUS) ──

```

+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   BACKGROUND IMAGE PLACEHOLDER:                                                                         |
|   [ Dark cinematic motorcycle under warm urban night lighting / moody asphalt tones ]                    |
|                                                                                                         |
|   FEDERATION OF HARLEY-DAVIDSON CLUBS OF EUROPE                                                         |
|   PM 2026 VILNIUS                                                                              |
|   Presidents' Meeting                                                                          |

|  |
| --- |
| [ICON] DATE: 23-25 October 2026 |
| --------------------------------------------------------------------------------------------------- |
|  |
| [ BUTTON: Register Now ] |
|  |
| +---------------------------------------------------------------------------------------------------------+ |

```
### UI Element Details & Specifications
* **Sizing:** Full viewport height container (100vh minus header spacing).
* **Content Stack:** Left-aligned or centered block layout. Text content utilizes clean dropshadow styling to maintain absolute readability over structural background imagery.
* **Primary Call-to-Action:** Centralized, larger accent-colored button with immediate smooth-scroll anchor targeting Component 7 (Registration Flow).

---

## ── COMPONENT 3: EVENT SUMMARY & VALUE PROP CARDS ──

```

+---------------------------------------------------------------------------------------------------------+
|   THE GATHERING                                                                                         |
|   Let's meet all Harley-Davidson People in Vilnius!                                            |
|   The 2026 Presidents' Meeting brings approved federation clubs to Vilnius for a focused weekend... |
|                                                                                                         |
|   +--------------------------+  +--------------------------+  +--------------------------+              |
|   | [ICON: Badge]            |  | [ICON: Map Pin]          |  | [ICON: Building]         |              |
|   | 70+ Active Clubs         |  | Vilnius Host City        |  | Park Plaza Event Venue   |              |
|   +--------------------------+  +--------------------------+  +--------------------------+              |
+---------------------------------------------------------------------------------------------------------+

```
### UI Element Details & Specifications
* **Layout Structure:** 3-column structural layout for desktop, stacked single-column view on mobile screens.
* **Card Framework:** Lightly tinted background boxes with subtle micro-borders (`1px solid #2D2D2D`) to anchor structural layout patterns cleanly.

---

## ── COMPONENT 4: VENUE DETAILS MATRIX ──

```

+---------------------------------------------------------------------------------------------------------+
|   VENUE HUB                                                                                             |
|   Hotel Park Plaza                                                                             |
|                                                                                                         |
|   +---------------------------------------------------+  +-------------------------------------------+  |
|   | TEXT FIELD / CONTENT AREA                         |  | IMAGE AREA PLACEHOLDER                    |  |
|   | [ICON: Verified] Official FH-DCE Event            |  |                                           |  |
|   |                                                   |  | [ Hotel Park Plaza Exterior Visual ]     |  |
|   | Vilnius Park Plaza Hotel is the official venue    |  |                                           |  |
|   | for PM 2026 Vilnius and the main reference point. |  |                                           |  |
|   |                                                   |  |                                           |  |
|   | [ICON: Location] Čiurlionio g. 84, Vilnius        |  |                                           |  |
|   +---------------------------------------------------+  +-------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+

```
### UI Element Details & Specifications
* **Structural Grid:** Balanced 50% / 50% split container layout.
* **Typography Hierarchy:** H2 accent header followed by small utility icons to cleanly delineate address blocks and metadata parameters.

---

## ── COMPONENT 5: ITINERARY TIMETABLE TABLE ──

```

+---------------------------------------------------------------------------------------------------------+
|   THE ITINERARY                                                                                         |
|   FH-DCE Presidents' Meeting 2026 Timetable                                                    |
|                                                                                                         |
|   ===================================================================================================   |

| THURSDAY (OCT 22, 2026) -- ARRIVAL |
| --- |
| 09:00 - 21:00 |
| =================================================================================================== |
| FRIDAY (OCT 23, 2026) -- ARRIVAL & WELCOME PARTY |
| --------------------------------------------------------------------------------------------------- |
| 09:00 - 21:00 |
| 20:00 - 01:00 |
| =================================================================================================== |
| SATURDAY (OCT 24, 2026) -- MEETING, EXCURSION & PARTY |
| --------------------------------------------------------------------------------------------------- |
| 10:00 - 17:00 |
| 10:00 - 16:00 |
| 20:00 - 01:00 |
| =================================================================================================== |
| SUNDAY / MONDAY |
| =================================================================================================== |
| +---------------------------------------------------------------------------------------------------------+ |

```
### UI Element Details & Specifications
* **Layout Paradigm:** Highly structured chronological grid mapping columns for Time window, Event Title, and Specific Room/Location.
* **Zebra Striping Style:** Alternating rows leverage deep muted background fills (`#1A1A1A` vs `#222222`) to guarantee cross-row readability across high density parameters.

---

## ── COMPONENT 6: EXCURSION HIGHLIGHT SECTION ──

```

+---------------------------------------------------------------------------------------------------------+
|   TOUR OVERVIEW                                                                                         |
|   Vilnius & Trakai Tour                                                                        |
|                                                                                                         |
|   +-------------------------------------------+  +---------------------------------------------------+  |
|   | IMAGE AREA PLACEHOLDER                    |  | TOUR DATA CARDS                                   |  |
|   |                                           |  | Discover Vilnius and historic Trakai on a guided  |  |
|   | [ Trakai Island Castle Image ]            |  | day tour featuring sightseeing, cruises, tasting. |  |
|   |                                           |  |                                                   |  |
|   |                                           |  | [ICON] DURATION: 5-6 Hours (10:00 - 16:00)       |  |
|   |                                           |  | [ICON] INCLUDED: Traditional Kibinai Tasting      |  |
|   |                                           |  | [ICON] PRICE: 65 EUR per person                   |  |
|   +-------------------------------------------+  +---------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+

```
### UI Element Details & Specifications
* **Layout Setup:** Media asset block oriented on the left pane, structured content list blocks floating on the right side.
* **Data Highlights:** Key informational tokens (Duration, Inclusions, Pricing matrices) utilize clean inline typographic groupings for minimal visual layout friction.

---

## ── COMPONENT 7: STEP-BY-STEP REGISTRATION PROCESS ──

```

+---------------------------------------------------------------------------------------------------------+
|   REGISTRATION PROCESS                                                                                  |
|   Secure Your Club's Representation                                                             |
|                                                                                                         |
|   +-----------------+   +-----------------+   +-----------------+   +-----------------+   +-----------+ |
|   | 01              |   | 02              |   | 03              |   | 04              |   | [ICON]    | |
|   | Open Gateway /  |-->| Select Approved |-->| Complete data   |-->| Save & Review   |-->| SUBMIT    | |
|   | Login / Create  |   | Club Identity   |   | fields (Draft)  |   | final inputs    |   | Review    | |
|   +-----------------+   +-----------------+   +-----------------+   +-----------------+   +-----------+ |
+---------------------------------------------------------------------------------------------------------+

```
### UI Element Details & Specifications
* **Flow Layout:** Progression pattern. Renders as an interconnected horizontal step track on standard desktops, breaking down cleanly into a vertical list flow for smaller viewports.
* **Step UI Attributes:** Each individual step block clearly surfaces high-contrast step indices (`01`, `02`, etc.) to map workflow stages.

---

## ── COMPONENT 8: FAQS ACCORDION COMPONENT ──

```

+---------------------------------------------------------------------------------------------------------+
|   FREQUENTLY ASKED QUESTIONS                                                                            |
|                                                                                                         |

| [+] Who can register for the event? |
| --- |
| [-] Can our club save and continue later? |
| >> Yes, the registration flow is designed so that info can be saved as a draft for later review. |
| --------------------------------------------------------------------------------------------------- |
| [+] Payment Details |
| --------------------------------------------------------------------------------------------------- |
| [+] What information should we prepare? |
| +---------------------------------------------------------------------------------------------------------+ |

```
### UI Element Details & Specifications
* **Component Pattern:** Accordion layout engine. Clicking rows dynamically toggles content open states while shifting icon triggers seamlessly between expansion matrices `[+]` and `[-]`.
* **Dynamic Response Rule:** Single item focus mechanism ensures opening one tab auto-collapses open surrounding elements.

---

## ── COMPONENT 9: CONTEXT CONVERSION & GLOBAL FOOTER ──

```

+---------------------------------------------------------------------------------------------------------+
|   KEEP YOUR HARLEY DAVIDSON ON THE ROAD!                                                                |
|   Join 70+ Harley-Davidson Clubs in defining the future of the Federation.                       |
|   [ Button: Login ]    [ Button: Register Now ]                                                         |

|  |
| --- |
| NEED ASSISTANCE? General Inquiries: info@harleyclub.lt |
| --------------------------------------------------------------------------------------------------- |
| © 2026 PM VILNIUS |
| +---------------------------------------------------------------------------------------------------------+ |

```
### UI Element Details & Specifications
* **Conversion Anchor Block:** High-contrast baseline action container layout.
* **Contact Information:** Highlights direct anchor links (`mailto:info@harleyclub.lt`) to ensure immediate action triggers.
* **Footer Links:** Standard horizontal metadata elements handling copyright markers alongside primary legal disclosure actions.

---

## ── SYSTEM MODAL OVERLAYS ──

### 1. Website Password / Gatekeeper Screen

```

+---------------------------------------------------------+
| PM 2026 VILNIUS                                         |
|                                                         |
| Website Password                                        |
| [ Input Field: Enter Password                         ] |
|                                                         |
| [ Button: Enter Website ]                               |
+---------------------------------------------------------+

```

### 2. Login Modal Template

```

+---------------------------------------------------------+
| Login                                               [X] |
|                                                         |
| Email Address:                                          |
| [ Input Field: e.g., name@domain.com                  ] |
|                                                         |
| Password:                                               |
| [ Input Field: ********** ] |
|                                                         |
| [ Button: Login ]               [Link: Forgot Password?] |

|  |
| --- |
| New user? [Button: Create Account] |
| +---------------------------------------------------------+ |

```

### 3. Create Account Modal Template

```

+---------------------------------------------------------+
| Create Account                                      [X] |
|                                                         |
| Approved Club:                                          |
| [ Dropdown Selector: "Choose an approved club..."    v ] |
|                                                         |
| Contact Email:                                          |
| [ Input Field: Account email marker                   ] |
|                                                         |
| Password:                                               |
| [ Input Field: Create strong password                 ] |
|                                                         |
| [ Button: Create Account ]                              |
+---------------------------------------------------------+

```
"""

# Save the content to a file
file_path = "harleyclub_wireframe.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"File successfully created: {file_path}")



```

Your markdown wireframe file is ready


Here is the complete wireframe structural definition for the `harleyclub.lt` website (**PM 2026 Vilnius**) in `.md` format. It accurately models the layout blocks, text hierarchy, table arrays, and pop-up system modals present on the live page.

---

# Low-Fidelity Wireframe: PM 2026 VILNIUS

**URL:** [https://www.harleyclub.lt/](https://www.harleyclub.lt/)

**Event:** Federation of Harley-Davidson Clubs of Europe Presidents' Meeting (PM 2026)

**Target Device:** Desktop & Responsive Mobile Baseline

---

## ── GLOBAL STYLES & LAYOUT BASELINE ──

* **Color Palette:** Dark UI Framework. Deep charcoal/asphalt backgrounds (`#121212`), muted warm grey containers (`#1E1E1E`), chrome/silver highlights, and precise golden-orange accents for actions.
* **Typography:** Bold, clean uppercase sans-serif headings; highly legible geometric sans-serif for structured data tables, forms, and time-blocks.
* **Layout Style:** Single long-form landing page with clear block boundaries and structured component matrices.

---

## ── COMPONENT 1: GLOBAL HEADER & NAVIGATION ──

```
+---------------------------------------------------------------------------------------------------------+
| [LOGO: PM 2026 VILNIUS]    [Link: Event]  [Link: Location]  [Link: Schedule]  [Link: Tour]  [Link: FAQ] | [Login]  [Register Now] |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Sticky Header:** Sticks to top of screen on scroll with 90% opacity deep dark background blur.
* **Action Elements:**
* `[Login]`: Triggers the Authentication Modal. Plain text link with warm-grey hover accent.
* `[Register Now]`: High-priority CTA button. Bold filled background, rounded edges (4px), white text.


* **Responsive Behavior:** Collapses into a standard hamburger menu bar below 960px breakpoint.

---

## ── COMPONENT 2: HERO COMPONENT (CINEMATIC FOCUS) ──

```
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   BACKGROUND IMAGE PLACEHOLDER:                                                                         |
|   [ Dark cinematic motorcycle under warm urban night lighting / moody asphalt tones ]                    |
|                                                                                                         |
|   FEDERATION OF HARLEY-DAVIDSON CLUBS OF EUROPE                                                         |
|   <h1>PM 2026 VILNIUS</h1>                                                                              |
|   <h3>Presidents' Meeting</h3>                                                                          |
|                                                                                                         |
|   ---------------------------------------------------------------------------------------------------   |
|   [ICON] DATE: 23-25 October 2026                 |    [ICON] LOCATION: Vilnius, Lithuania             |
|   ---------------------------------------------------------------------------------------------------   |
|                                                                                                         |
|   [ BUTTON: Register Now ]                                                                              |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Sizing:** Full viewport height container (100vh minus header spacing).
* **Content Stack:** Left-aligned or centered block layout. Text content utilizes clean dropshadow styling to maintain absolute readability over structural background imagery.
* **Primary Call-to-Action:** Centralized, larger accent-colored button with immediate smooth-scroll anchor targeting Component 7 (Registration Flow).

---

## ── COMPONENT 3: EVENT SUMMARY & VALUE PROP CARDS ──

```
+---------------------------------------------------------------------------------------------------------+
|   THE GATHERING                                                                                         |
|   <h2>Let's meet all Harley-Davidson People in Vilnius!</h2>                                            |
|   <p>The 2026 Presidents' Meeting brings approved federation clubs to Vilnius for a focused weekend... </p>|
|                                                                                                         |
|   +--------------------------+  +--------------------------+  +--------------------------+              |
|   | [ICON: Badge]            |  | [ICON: Map Pin]          |  | [ICON: Building]         |              |
|   | 70+ Active Clubs         |  | Vilnius Host City        |  | Park Plaza Event Venue   |              |
|   +--------------------------+  +--------------------------+  +--------------------------+              |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Layout Structure:** 3-column structural layout for desktop, stacked single-column view on mobile screens.
* **Card Framework:** Lightly tinted background boxes with subtle micro-borders (`1px solid #2D2D2D`) to anchor structural layout patterns cleanly.

---

## ── COMPONENT 4: VENUE DETAILS MATRIX ──

```
+---------------------------------------------------------------------------------------------------------+
|   VENUE HUB                                                                                             |
|   <h2>Hotel Park Plaza</h2>                                                                             |
|                                                                                                         |
|   +---------------------------------------------------+  +-------------------------------------------+  |
|   | TEXT FIELD / CONTENT AREA                         |  | IMAGE AREA PLACEHOLDER                    |  |
|   | [ICON: Verified] Official FH-DCE Event            |  |                                           |  |
|   |                                                   |  | [ Hotel Park Plaza Exterior Visual ]     |  |
|   | Vilnius Park Plaza Hotel is the official venue    |  |                                           |  |
|   | for PM 2026 Vilnius and the main reference point. |  |                                           |  |
|   |                                                   |  |                                           |  |
|   | [ICON: Location] Čiurlionio g. 84, Vilnius        |  |                                           |  |
|   +---------------------------------------------------+  +-------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Structural Grid:** Balanced 50% / 50% split container layout.
* **Typography Hierarchy:** H2 accent header followed by small utility icons to cleanly delineate address blocks and metadata parameters.

---

## ── COMPONENT 5: ITINERARY TIMETABLE TABLE ──

```
+---------------------------------------------------------------------------------------------------------+
|   THE ITINERARY                                                                                         |
|   <h2>FH-DCE Presidents' Meeting 2026 Timetable</h2>                                                    |
|                                                                                                         |
|   ===================================================================================================   |
|   THURSDAY (OCT 22, 2026) -- ARRIVAL                                                                    |
|   ---------------------------------------------------------------------------------------------------   |
|   09:00 - 21:00          |  PM Registration             | Lobby - Park Plaza Hotel                  |
|   ===================================================================================================   |
|   FRIDAY (OCT 23, 2026) -- ARRIVAL & WELCOME PARTY                                                      |
|   ---------------------------------------------------------------------------------------------------   |
|   09:00 - 21:00          |  PM Registration             | Lobby - Park Plaza Hotel                  |
|   20:00 - 01:00          |  Welcome Party               | Main Restaurant - Park Plaza Hotel        |
|   ===================================================================================================   |
|   SATURDAY (OCT 24, 2026) -- MEETING, EXCURSION & PARTY                                                 |
|   ---------------------------------------------------------------------------------------------------   |
|   10:00 - 17:00          |  Presidents' Meeting         | Conf. Center - 1st Floor, Saphire Hall     |
|   10:00 - 16:00          |  Vilnius & Trakai Tour       | Main Entrance - Leaving at 10:00          |
|   20:00 - 01:00          |  FH-DCE Party                | Conf. Center - Saphire & Coral Halls      |
|   ===================================================================================================   |
|   SUNDAY / MONDAY        |  Checking out details...     | Hotel's Reception Desk                    |
|   ===================================================================================================   |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Layout Paradigm:** Highly structured chronological grid mapping columns for Time window, Event Title, and Specific Room/Location.
* **Zebra Striping Style:** Alternating rows leverage deep muted background fills (`#1A1A1A` vs `#222222`) to guarantee cross-row readability across high density parameters.

---

## ── COMPONENT 6: EXCURSION HIGHLIGHT SECTION ──

```
+---------------------------------------------------------------------------------------------------------+
|   TOUR OVERVIEW                                                                                         |
|   <h2>Vilnius & Trakai Tour</h2>                                                                        |
|                                                                                                         |
|   +-------------------------------------------+  +---------------------------------------------------+  |
|   | IMAGE AREA PLACEHOLDER                    |  | TOUR DATA CARDS                                   |  |
|   |                                           |  | Discover Vilnius and historic Trakai on a guided  |  |
|   | [ Trakai Island Castle Image ]            |  | day tour featuring sightseeing, cruises, tasting. |  |
|   |                                           |  |                                                   |  |
|   |                                           |  | [ICON] DURATION: 5-6 Hours (10:00 - 16:00)       |  |
|   |                                           |  | [ICON] INCLUDED: Traditional Kibinai Tasting      |  |
|   |                                           |  | [ICON] PRICE: 65 EUR per person                   |  |
|   +-------------------------------------------+  +---------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Layout Setup:** Media asset block oriented on the left pane, structured content list blocks floating on the right side.
* **Data Highlights:** Key informational tokens (Duration, Inclusions, Pricing matrices) utilize clean inline typographic groupings for minimal visual layout friction.

---

## ── COMPONENT 7: STEP-BY-STEP REGISTRATION PROCESS ──

```
+---------------------------------------------------------------------------------------------------------+
|   REGISTRATION PROCESS                                                                                  |
|   <h2>Secure Your Club's Representation</h2>                                                             |
|                                                                                                         |
|   +-----------------+   +-----------------+   +-----------------+   +-----------------+   +-----------+ |
|   | 01              |   | 02              |   | 03              |   | 04              |   | [ICON]    | |
|   | Open Gateway /  |-->| Select Approved |-->| Complete data   |-->| Save & Review   |-->| SUBMIT    | |
|   | Login / Create  |   | Club Identity   |   | fields (Draft)  |   | final inputs    |   | Review    | |
|   +-----------------+   +-----------------+   +-----------------+   +-----------------+   +-----------+ |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Flow Layout:** Progression pattern. Renders as an interconnected horizontal step track on standard desktops, breaking down cleanly into a vertical list flow for smaller viewports.
* **Step UI Attributes:** Each individual step block clearly surfaces high-contrast step indices (`01`, `02`, etc.) to map workflow stages.

---

## ── COMPONENT 8: FAQS ACCORDION COMPONENT ──

```
+---------------------------------------------------------------------------------------------------------+
|   FREQUENTLY ASKED QUESTIONS                                                                            |
|                                                                                                         |
|   [+] Who can register for the event?                                                                   |
|   ---------------------------------------------------------------------------------------------------   |
|   [-] Can our club save and continue later?                                                             |
|       >> Yes, the registration flow is designed so that info can be saved as a draft for later review.  |
|   ---------------------------------------------------------------------------------------------------   |
|   [+] Payment Details                                                                                   |
|   ---------------------------------------------------------------------------------------------------   |
|   [+] What information should we prepare?                                                               |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Component Pattern:** Accordion layout engine. Clicking rows dynamically toggles content open states while shifting icon triggers seamlessly between expansion matrices `[+]` and `[-]`.
* **Dynamic Response Rule:** Single item focus mechanism ensures opening one tab auto-collapses open surrounding elements.

---

## ── COMPONENT 9: CONTEXT CONVERSION & GLOBAL FOOTER ──

```
+---------------------------------------------------------------------------------------------------------+
|   KEEP YOUR HARLEY DAVIDSON ON THE ROAD!                                                                |
|   <p>Join 70+ Harley-Davidson Clubs in defining the future of the Federation.</p>                       |
|   [ Button: Login ]    [ Button: Register Now ]                                                         |
|                                                                                                         |
|   ---------------------------------------------------------------------------------------------------   |
|   NEED ASSISTANCE? General Inquiries: info@harleyclub.lt                                                |
|   ---------------------------------------------------------------------------------------------------   |
|   © 2026 PM VILNIUS | [Link: Privacy Policy]                                                            |
+---------------------------------------------------------------------------------------------------------+

```

### UI Element Details & Specifications

* **Conversion Anchor Block:** High-contrast baseline action container layout.
* **Contact Information:** Highlights direct anchor links (`mailto:info@harleyclub.lt`) to ensure immediate action triggers.
* **Footer Links:** Standard horizontal metadata elements handling copyright markers alongside primary legal disclosure actions.

---

## ── SYSTEM MODAL OVERLAYS ──

### 1. Website Password / Gatekeeper Screen

```
+---------------------------------------------------------+
| PM 2026 VILNIUS                                         |
|                                                         |
| Website Password                                        |
| [ Input Field: Enter Password                         ] |
|                                                         |
| [ Button: Enter Website ]                               |
+---------------------------------------------------------+

```

### 2. Login Modal Template

```
+---------------------------------------------------------+
| Login                                               [X] |
|                                                         |
| Email Address:                                          |
| [ Input Field: e.g., name@domain.com                  ] |
|                                                         |
| Password:                                               |
| [ Input Field: ********** ] |
|                                                         |
| [ Button: Login ]               [Link: Forgot Password?] |
|                                                         |
| ------------------------------------------------------- |
| New user? [Button: Create Account]                      |
+---------------------------------------------------------+

```

### 3. Create Account Modal Template

```
+---------------------------------------------------------+
| Create Account                                      [X] |
|                                                         |
| Approved Club:                                          |
| [ Dropdown Selector: "Choose an approved club..."    v ] |
|                                                         |
| Contact Email:                                          |
| [ Input Field: Account email marker                   ] |
|                                                         |
| Password:                                               |
| [ Input Field: Create strong password                 ] |
|                                                         |
| [ Button: Create Account ]                              |
+---------------------------------------------------------+

```