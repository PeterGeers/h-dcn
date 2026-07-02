"""
PDF translation utilities for H-DCN order confirmation and membership documents.

Provides localized static text, date formatting, and currency formatting for
PDF generation across all 8 supported locales. Dutch (nl) is the fallback
for missing keys or unsupported locales.
"""

from datetime import datetime

from shared.i18n.locale_resolver import SUPPORTED_LOCALES, DEFAULT_LOCALE


# Month names per locale for date formatting
_MONTH_NAMES: dict[str, list[str]] = {
    "nl": [
        "januari", "februari", "maart", "april", "mei", "juni",
        "juli", "augustus", "september", "oktober", "november", "december",
    ],
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
    "fr": [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ],
    "de": [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ],
    "sv": [
        "januari", "februari", "mars", "april", "maj", "juni",
        "juli", "augusti", "september", "oktober", "november", "december",
    ],
    "da": [
        "januar", "februar", "marts", "april", "maj", "juni",
        "juli", "august", "september", "oktober", "november", "december",
    ],
    "it": [
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ],
    "es": [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ],
}


PDF_TRANSLATIONS: dict[str, dict[str, str]] = {
    "nl": {
        "document_title": "Orderbevestiging",
        "order_number": "Ordernummer",
        "order_date": "Orderdatum",
        "customer": "Klant",
        "delivery_address": "Afleveradres",
        "billing_address": "Factuuradres",
        "product": "Product",
        "option": "Optie",
        "quantity": "Aantal",
        "unit_price": "Stukprijs",
        "total": "Totaal",
        "subtotal": "Subtotaal",
        "shipping": "Verzendkosten",
        "grand_total": "Eindtotaal",
        "total_paid": "Totaal betaald",
        "ordered_products": "Bestelde producten",
        "delivery": "Levering",
        "status": "Status",
        "status_pending": "In behandeling",
        "status_paid": "Betaald",
        "status_shipped": "Verzonden",
        "status_delivered": "Afgeleverd",
        "status_cancelled": "Geannuleerd",
        "page": "Pagina",
        "of": "van",
        "no_data": "Geen gegevens beschikbaar",
        "thank_you_message": "Bedankt voor uw bestelling!",
        # Packing slip
        "packing_slip_title": "Pakbon",
        "pick_check": "✓",
        "delivery_method": "Leverwijze",
        "pickup_location": "Afhaallocatie",
        "recipient": "Ontvanger",
        # Shipping label
        "shipping_label_title": "Verzendlabel",
        "order_ref": "Ordernr",
    },
    "en": {
        "document_title": "Order Confirmation",
        "order_number": "Order Number",
        "order_date": "Order Date",
        "customer": "Customer",
        "delivery_address": "Delivery Address",
        "billing_address": "Billing Address",
        "product": "Product",
        "option": "Option",
        "quantity": "Quantity",
        "unit_price": "Unit Price",
        "total": "Total",
        "subtotal": "Subtotal",
        "shipping": "Shipping",
        "grand_total": "Grand Total",
        "total_paid": "Total Paid",
        "ordered_products": "Ordered Products",
        "delivery": "Delivery",
        "status": "Status",
        "status_pending": "Pending",
        "status_paid": "Paid",
        "status_shipped": "Shipped",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled",
        "page": "Page",
        "of": "of",
        "no_data": "No data available",
        "thank_you_message": "Thank you for your order!",
        # Packing slip
        "packing_slip_title": "Packing Slip",
        "pick_check": "✓",
        "delivery_method": "Delivery Method",
        "pickup_location": "Pickup Location",
        "recipient": "Recipient",
        # Shipping label
        "shipping_label_title": "Shipping Label",
        "order_ref": "Order No",
    },
    "fr": {
        "document_title": "Confirmation de commande",
        "order_number": "Numéro de commande",
        "order_date": "Date de commande",
        "customer": "Client",
        "delivery_address": "Adresse de livraison",
        "billing_address": "Adresse de facturation",
        "product": "Produit",
        "option": "Option",
        "quantity": "Quantité",
        "unit_price": "Prix unitaire",
        "total": "Total",
        "subtotal": "Sous-total",
        "shipping": "Frais de livraison",
        "grand_total": "Total général",
        "total_paid": "Total payé",
        "ordered_products": "Produits commandés",
        "delivery": "Livraison",
        "status": "Statut",
        "status_pending": "En attente",
        "status_paid": "Payé",
        "status_shipped": "Expédié",
        "status_delivered": "Livré",
        "status_cancelled": "Annulé",
        "page": "Page",
        "of": "de",
        "no_data": "Aucune donnée disponible",
        "thank_you_message": "Merci pour votre commande !",
        # Packing slip
        "packing_slip_title": "Bon de livraison",
        "pick_check": "✓",
        "delivery_method": "Mode de livraison",
        "pickup_location": "Lieu de retrait",
        "recipient": "Destinataire",
        # Shipping label
        "shipping_label_title": "Étiquette d'expédition",
        "order_ref": "N° commande",
    },
    "de": {
        "document_title": "Auftragsbestätigung",
        "order_number": "Bestellnummer",
        "order_date": "Bestelldatum",
        "customer": "Kunde",
        "delivery_address": "Lieferadresse",
        "billing_address": "Rechnungsadresse",
        "product": "Produkt",
        "option": "Option",
        "quantity": "Menge",
        "unit_price": "Stückpreis",
        "total": "Gesamt",
        "subtotal": "Zwischensumme",
        "shipping": "Versandkosten",
        "grand_total": "Gesamtbetrag",
        "total_paid": "Gesamt bezahlt",
        "ordered_products": "Bestellte Produkte",
        "delivery": "Lieferung",
        "status": "Status",
        "status_pending": "In Bearbeitung",
        "status_paid": "Bezahlt",
        "status_shipped": "Versendet",
        "status_delivered": "Zugestellt",
        "status_cancelled": "Storniert",
        "page": "Seite",
        "of": "von",
        "no_data": "Keine Daten verfügbar",
        "thank_you_message": "Vielen Dank für Ihre Bestellung!",
        # Packing slip
        "packing_slip_title": "Lieferschein",
        "pick_check": "✓",
        "delivery_method": "Liefermethode",
        "pickup_location": "Abholort",
        "recipient": "Empfänger",
        # Shipping label
        "shipping_label_title": "Versandetikett",
        "order_ref": "Bestell-Nr",
    },
    "sv": {
        "document_title": "Orderbekräftelse",
        "order_number": "Ordernummer",
        "order_date": "Orderdatum",
        "customer": "Kund",
        "delivery_address": "Leveransadress",
        "billing_address": "Faktureringsadress",
        "product": "Produkt",
        "option": "Alternativ",
        "quantity": "Antal",
        "unit_price": "Styckpris",
        "total": "Totalt",
        "subtotal": "Delsumma",
        "shipping": "Frakt",
        "grand_total": "Slutsumma",
        "total_paid": "Totalt betalt",
        "ordered_products": "Beställda produkter",
        "delivery": "Leverans",
        "status": "Status",
        "status_pending": "Väntande",
        "status_paid": "Betald",
        "status_shipped": "Skickad",
        "status_delivered": "Levererad",
        "status_cancelled": "Avbruten",
        "page": "Sida",
        "of": "av",
        "no_data": "Inga uppgifter tillgängliga",
        "thank_you_message": "Tack för din beställning!",
        # Packing slip
        "packing_slip_title": "Följesedel",
        "pick_check": "✓",
        "delivery_method": "Leveransmetod",
        "pickup_location": "Upphämtningsplats",
        "recipient": "Mottagare",
        # Shipping label
        "shipping_label_title": "Fraktetikett",
        "order_ref": "Ordernr",
    },
    "da": {
        "document_title": "Ordrebekræftelse",
        "order_number": "Ordrenummer",
        "order_date": "Ordredato",
        "customer": "Kunde",
        "delivery_address": "Leveringsadresse",
        "billing_address": "Faktureringsadresse",
        "product": "Produkt",
        "option": "Mulighed",
        "quantity": "Antal",
        "unit_price": "Stykpris",
        "total": "Total",
        "subtotal": "Subtotal",
        "shipping": "Forsendelse",
        "grand_total": "Samlet total",
        "total_paid": "Samlet betalt",
        "ordered_products": "Bestilte produkter",
        "delivery": "Levering",
        "status": "Status",
        "status_pending": "Afventer",
        "status_paid": "Betalt",
        "status_shipped": "Afsendt",
        "status_delivered": "Leveret",
        "status_cancelled": "Annulleret",
        "page": "Side",
        "of": "af",
        "no_data": "Ingen data tilgængelig",
        "thank_you_message": "Tak for din bestilling!",
        # Packing slip
        "packing_slip_title": "Følgeseddel",
        "pick_check": "✓",
        "delivery_method": "Leveringsmetode",
        "pickup_location": "Afhentningssted",
        "recipient": "Modtager",
        # Shipping label
        "shipping_label_title": "Forsendelseslabel",
        "order_ref": "Ordrenr",
    },
    "it": {
        "document_title": "Conferma dell'ordine",
        "order_number": "Numero d'ordine",
        "order_date": "Data dell'ordine",
        "customer": "Cliente",
        "delivery_address": "Indirizzo di consegna",
        "billing_address": "Indirizzo di fatturazione",
        "product": "Prodotto",
        "option": "Opzione",
        "quantity": "Quantità",
        "unit_price": "Prezzo unitario",
        "total": "Totale",
        "subtotal": "Subtotale",
        "shipping": "Spedizione",
        "grand_total": "Totale complessivo",
        "total_paid": "Totale pagato",
        "ordered_products": "Prodotti ordinati",
        "delivery": "Consegna",
        "status": "Stato",
        "status_pending": "In attesa",
        "status_paid": "Pagato",
        "status_shipped": "Spedito",
        "status_delivered": "Consegnato",
        "status_cancelled": "Annullato",
        "page": "Pagina",
        "of": "di",
        "no_data": "Nessun dato disponibile",
        "thank_you_message": "Grazie per il tuo ordine!",
        # Packing slip
        "packing_slip_title": "Bolla di consegna",
        "pick_check": "✓",
        "delivery_method": "Metodo di consegna",
        "pickup_location": "Luogo di ritiro",
        "recipient": "Destinatario",
        # Shipping label
        "shipping_label_title": "Etichetta di spedizione",
        "order_ref": "N° ordine",
    },
    "es": {
        "document_title": "Confirmación de pedido",
        "order_number": "Número de pedido",
        "order_date": "Fecha de pedido",
        "customer": "Cliente",
        "delivery_address": "Dirección de entrega",
        "billing_address": "Dirección de facturación",
        "product": "Producto",
        "option": "Opción",
        "quantity": "Cantidad",
        "unit_price": "Precio unitario",
        "total": "Total",
        "subtotal": "Subtotal",
        "shipping": "Envío",
        "grand_total": "Total general",
        "total_paid": "Total pagado",
        "ordered_products": "Productos pedidos",
        "delivery": "Entrega",
        "status": "Estado",
        "status_pending": "Pendiente",
        "status_paid": "Pagado",
        "status_shipped": "Enviado",
        "status_delivered": "Entregado",
        "status_cancelled": "Cancelado",
        "page": "Página",
        "of": "de",
        "no_data": "No hay datos disponibles",
        "thank_you_message": "¡Gracias por su pedido!",
        # Packing slip
        "packing_slip_title": "Albarán",
        "pick_check": "✓",
        "delivery_method": "Método de entrega",
        "pickup_location": "Lugar de recogida",
        "recipient": "Destinatario",
        # Shipping label
        "shipping_label_title": "Etiqueta de envío",
        "order_ref": "N° pedido",
    },
}


def get_pdf_text(key: str, locale: str) -> str:
    """
    Get a translated PDF text string for the given key and locale.

    Falls back to Dutch (nl) if the locale is not supported or the key
    is not found in the requested locale's translations.

    Args:
        key: The translation key (e.g., "document_title", "order_number").
        locale: The locale code (e.g., "en", "fr", "de").

    Returns:
        The translated string, or the Dutch fallback, or the key itself
        if not found in any locale.
    """
    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if resolved_locale not in SUPPORTED_LOCALES:
        resolved_locale = DEFAULT_LOCALE

    # Try the requested locale first
    locale_translations = PDF_TRANSLATIONS.get(resolved_locale, {})
    text = locale_translations.get(key, "")

    if text:
        return text

    # Fallback to Dutch
    nl_translations = PDF_TRANSLATIONS.get(DEFAULT_LOCALE, {})
    nl_text = nl_translations.get(key, "")

    if nl_text:
        return nl_text

    # Last resort: return the key itself
    return key


def format_date_for_locale(date: datetime, locale: str) -> str:
    """
    Format a datetime according to the locale's date convention.

    Formats:
        nl: "15 januari 2025"
        en: "15 January 2025"
        fr: "15 janvier 2025"
        de: "15. Januar 2025"
        sv: "15 januari 2025"
        da: "15. januar 2025"
        it: "15 gennaio 2025"
        es: "15 de enero de 2025"

    Args:
        date: The datetime object to format.
        locale: The locale code.

    Returns:
        A locale-formatted date string. Returns empty string if date is None.
    """
    if date is None:
        return ""

    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if resolved_locale not in SUPPORTED_LOCALES:
        resolved_locale = DEFAULT_LOCALE

    day = date.day
    month_names = _MONTH_NAMES.get(resolved_locale, _MONTH_NAMES[DEFAULT_LOCALE])
    month = month_names[date.month - 1]
    year = date.year

    if resolved_locale == "de":
        return f"{day}. {month} {year}"
    elif resolved_locale == "da":
        return f"{day}. {month} {year}"
    elif resolved_locale == "es":
        return f"{day} de {month} de {year}"
    else:
        # nl, en, fr, sv, it
        return f"{day} {month} {year}"


def format_currency_for_locale(amount: float, locale: str) -> str:
    """
    Format a EUR currency amount with locale-appropriate formatting.

    Formats:
        nl: "€ 1.234,56"
        en: "€1,234.56"
        fr: "1 234,56 €"
        de: "1.234,56 €"
        sv: "1 234,56 €"
        da: "1.234,56 €"
        it: "1.234,56 €"
        es: "1.234,56 €"

    Args:
        amount: The numeric amount to format.
        locale: The locale code.

    Returns:
        A locale-formatted EUR currency string. Returns empty string if amount is None.
    """
    if amount is None:
        return ""

    resolved_locale = locale.strip().lower() if locale and isinstance(locale, str) else DEFAULT_LOCALE

    if resolved_locale not in SUPPORTED_LOCALES:
        resolved_locale = DEFAULT_LOCALE

    # Format the number parts
    is_negative = amount < 0
    abs_amount = abs(amount)

    # Split into integer and decimal parts with 2 decimal places
    integer_part = int(abs_amount)
    decimal_part = round((abs_amount - integer_part) * 100)

    # Handle rounding edge case (e.g., 99.999 -> decimal_part = 100)
    if decimal_part >= 100:
        integer_part += 1
        decimal_part = 0

    decimal_str = f"{decimal_part:02d}"

    # Format integer part with thousands separators
    if resolved_locale in ("en",):
        # Comma as thousands separator, dot as decimal
        int_str = _format_thousands(integer_part, ",")
        formatted = f"{int_str}.{decimal_str}"
    elif resolved_locale in ("fr", "sv"):
        # Space as thousands separator, comma as decimal
        int_str = _format_thousands(integer_part, "\u00a0")  # non-breaking space
        formatted = f"{int_str},{decimal_str}"
    else:
        # nl, de, da, it, es: dot as thousands separator, comma as decimal
        int_str = _format_thousands(integer_part, ".")
        formatted = f"{int_str},{decimal_str}"

    if is_negative:
        formatted = f"-{formatted}"

    # Position the Euro symbol
    if resolved_locale == "nl":
        return f"\u20ac\u00a0{formatted}"  # "€ 1.234,56" (non-breaking space)
    elif resolved_locale == "en":
        return f"\u20ac{formatted}"  # "€1,234.56"
    else:
        # fr, de, sv, da, it, es: symbol after with non-breaking space
        return f"{formatted}\u00a0\u20ac"  # "1.234,56 €"


def _format_thousands(value: int, separator: str) -> str:
    """
    Format an integer with the specified thousands separator.

    Args:
        value: The integer to format.
        separator: The thousands separator character.

    Returns:
        The formatted string with thousands separators.
    """
    if value == 0:
        return "0"

    result = ""
    s = str(value)
    length = len(s)

    for i, digit in enumerate(s):
        if i > 0 and (length - i) % 3 == 0:
            result += separator
        result += digit

    return result
