// Core H-DCN Types
export interface Member {
  id: string;
  member_id?: string;
  name: string;
  email: string;
  region: string;
  regio?: string;
  membershipType: string;
  membership_type?: string;
  lidmaatschap?: string;
  voornaam?: string;
  achternaam?: string;
  lidnummer?: string | number;
  status?: string;
  created_at?: string;
  updated_at?: string;
  initialen?: string;
  tussenvoegsel?: string;
  geboortedatum?: string;
  geslacht?: string;
  telefoon?: string;
  phone?: string;
  mobiel?: string;
  werktelefoon?: string;
  bsn?: string;
  nationaliteit?: string;
  straat?: string;
  huisnummer?: string;
  postcode?: string;
  woonplaats?: string;
  land?: string;
  postadres?: string;
  postpostcode?: string;
  postwoonplaats?: string;
  postland?: string;
  clubblad?: string;
  nieuwsbrief?: string;
  ingangsdatum?: string;
  einddatum?: string;
  opzegtermijn?: string;
  motormerk?: string;
  motortype?: string;
  motormodel?: string;
  motorkleur?: string;
  bouwjaar?: string;
  kenteken?: string;
  cilinderinhoud?: string;
  vermogen?: string;
  bankrekeningnummer?: string;
  iban?: string;
  bic?: string;
  contributie?: string;
  betaalwijze?: string;
  incasso?: string;
  beroep?: string;
  werkgever?: string;
  hobbys?: string;
  wiewatwaar?: string;
  minderjarigNaam?: string;
  notities?: string;
  opmerkingen?: string;
  privacy?: string;
  toestemmingfoto?: string;
  address?: string;
  // Additional timestamp and membership fields
  tijdstempel?: string;
  aanmeldingsjaar?: string;
  datum_ondertekening?: string;
  datumOndertekening?: string;
  ingangsdatum_lidmaatschap?: string;
  ingangsdatumLidmaatschap?: string;
  aanmeldingsdatum?: string;
  aanmeldingsDatum?: string;
}

export interface Product {
  id: string;
  name: string;
  naam?: string;
  price: number;
  prijs?: string | number;
  category: string;
  groep?: string;
  subgroep?: string;
  opties?: any[];
}

export interface Event {
  event_id?: string;
  title?: string;
  naam?: string;
  event_date?: string;
  datum_van?: string;
  end_date?: string;
  datum_tot?: string;
  location?: string;
  locatie?: string;
  region?: string;
  regio?: string;
  participants?: string | number;
  aantal_deelnemers?: string | number;
  cost?: string | number;
  kosten?: string | number;
  revenue?: string | number;
  inkomsten?: string | number;
  notes?: string;
  opmerkingen?: string;
  betaalstatus?: string;
  factuurnummer?: string;
}

export interface ApiResponse<T> {
  statusCode: number;
  body: T;
}

// Cognito User Groups
export type UserGroup = 'hdcnLeden' | 'hdcnAdmins' | `hdcnRegio_${string}`;