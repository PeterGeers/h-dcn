"""
Localized API error messages for H-DCN backend.

Provides translated error messages for all common API errors across 8 supported
locales (nl, en, fr, de, sv, da, it, es). Falls back to Dutch (nl) for unknown
locales or missing error keys.

Requirements validated: 6.2, 6.3, 6.4
"""

from shared.i18n.locale_resolver import SUPPORTED_LOCALES, DEFAULT_LOCALE, is_valid_locale


# Structure: { error_key: { locale: message } }
ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "authorization_required": {
        "nl": "Autorisatie vereist",
        "en": "Authorization required",
        "fr": "Autorisation requise",
        "de": "Autorisierung erforderlich",
        "sv": "Auktorisering krävs",
        "da": "Autorisation påkrævet",
        "it": "Autorizzazione richiesta",
        "es": "Autorización requerida",
    },
    "forbidden": {
        "nl": "Toegang geweigerd",
        "en": "Access denied",
        "fr": "Accès refusé",
        "de": "Zugriff verweigert",
        "sv": "Åtkomst nekad",
        "da": "Adgang nægtet",
        "it": "Accesso negato",
        "es": "Acceso denegado",
    },
    "not_found": {
        "nl": "Niet gevonden",
        "en": "Not found",
        "fr": "Non trouvé",
        "de": "Nicht gefunden",
        "sv": "Hittades inte",
        "da": "Ikke fundet",
        "it": "Non trovato",
        "es": "No encontrado",
    },
    "validation_error": {
        "nl": "Validatiefout",
        "en": "Validation error",
        "fr": "Erreur de validation",
        "de": "Validierungsfehler",
        "sv": "Valideringsfel",
        "da": "Valideringsfejl",
        "it": "Errore di validazione",
        "es": "Error de validación",
    },
    "internal_error": {
        "nl": "Interne serverfout",
        "en": "Internal server error",
        "fr": "Erreur interne du serveur",
        "de": "Interner Serverfehler",
        "sv": "Internt serverfel",
        "da": "Intern serverfejl",
        "it": "Errore interno del server",
        "es": "Error interno del servidor",
    },
    "member_not_found": {
        "nl": "Lid niet gevonden",
        "en": "Member not found",
        "fr": "Membre non trouvé",
        "de": "Mitglied nicht gefunden",
        "sv": "Medlem hittades inte",
        "da": "Medlem ikke fundet",
        "it": "Membro non trovato",
        "es": "Miembro no encontrado",
    },
    "member_already_exists": {
        "nl": "Lid bestaat al",
        "en": "Member already exists",
        "fr": "Le membre existe déjà",
        "de": "Mitglied existiert bereits",
        "sv": "Medlem finns redan",
        "da": "Medlem eksisterer allerede",
        "it": "Il membro esiste già",
        "es": "El miembro ya existe",
    },
    "invalid_input": {
        "nl": "Ongeldige invoer",
        "en": "Invalid input",
        "fr": "Entrée invalide",
        "de": "Ungültige Eingabe",
        "sv": "Ogiltig inmatning",
        "da": "Ugyldig indtastning",
        "it": "Input non valido",
        "es": "Entrada no válida",
    },
    "payment_failed": {
        "nl": "Betaling mislukt",
        "en": "Payment failed",
        "fr": "Paiement échoué",
        "de": "Zahlung fehlgeschlagen",
        "sv": "Betalning misslyckades",
        "da": "Betaling mislykkedes",
        "it": "Pagamento fallito",
        "es": "Pago fallido",
    },
    "order_not_found": {
        "nl": "Bestelling niet gevonden",
        "en": "Order not found",
        "fr": "Commande non trouvée",
        "de": "Bestellung nicht gefunden",
        "sv": "Beställning hittades inte",
        "da": "Ordre ikke fundet",
        "it": "Ordine non trovato",
        "es": "Pedido no encontrado",
    },
    "product_not_found": {
        "nl": "Product niet gevonden",
        "en": "Product not found",
        "fr": "Produit non trouvé",
        "de": "Produkt nicht gefunden",
        "sv": "Produkt hittades inte",
        "da": "Produkt ikke fundet",
        "it": "Prodotto non trovato",
        "es": "Producto no encontrado",
    },
    "cart_empty": {
        "nl": "Winkelwagen is leeg",
        "en": "Cart is empty",
        "fr": "Le panier est vide",
        "de": "Warenkorb ist leer",
        "sv": "Varukorgen är tom",
        "da": "Indkøbskurven er tom",
        "it": "Il carrello è vuoto",
        "es": "El carrito está vacío",
    },
    "insufficient_stock": {
        "nl": "Onvoldoende voorraad",
        "en": "Insufficient stock",
        "fr": "Stock insuffisant",
        "de": "Unzureichender Bestand",
        "sv": "Otillräckligt lager",
        "da": "Utilstrækkelig lagerbeholdning",
        "it": "Scorte insufficienti",
        "es": "Stock insuficiente",
    },
    "email_already_exists": {
        "nl": "E-mailadres is al in gebruik",
        "en": "Email address already in use",
        "fr": "Adresse e-mail déjà utilisée",
        "de": "E-Mail-Adresse wird bereits verwendet",
        "sv": "E-postadressen används redan",
        "da": "E-mailadressen er allerede i brug",
        "it": "Indirizzo e-mail già in uso",
        "es": "Dirección de correo electrónico ya en uso",
    },
    "invalid_membership": {
        "nl": "Ongeldig lidmaatschap",
        "en": "Invalid membership",
        "fr": "Adhésion invalide",
        "de": "Ungültige Mitgliedschaft",
        "sv": "Ogiltigt medlemskap",
        "da": "Ugyldigt medlemskab",
        "it": "Abbonamento non valido",
        "es": "Membresía no válida",
    },
}

# Default fallback message for unknown error keys
_UNKNOWN_ERROR_MESSAGES: dict[str, str] = {
    "nl": "Er is een fout opgetreden",
    "en": "An error occurred",
    "fr": "Une erreur s'est produite",
    "de": "Ein Fehler ist aufgetreten",
    "sv": "Ett fel uppstod",
    "da": "Der opstod en fejl",
    "it": "Si è verificato un errore",
    "es": "Se produjo un error",
}


def get_error_message(error_key: str, locale: str) -> str:
    """
    Get a localized error message with Dutch (nl) fallback.

    Looks up the error_key in ERROR_MESSAGES for the given locale. Falls back
    to Dutch if the locale is invalid/unsupported or the key is missing for
    that locale. Returns a generic Dutch error message for unknown error keys.

    Args:
        error_key: The stable error identifier (e.g., "authorization_required").
        locale: The locale code to retrieve the message in.

    Returns:
        A non-empty localized error message string.
    """
    # Normalize locale
    resolved_locale = DEFAULT_LOCALE
    if locale and isinstance(locale, str):
        normalized = locale.strip().lower()
        if is_valid_locale(normalized):
            resolved_locale = normalized

    # Look up the error key
    if error_key and isinstance(error_key, str) and error_key in ERROR_MESSAGES:
        messages = ERROR_MESSAGES[error_key]
        # Try requested locale, fall back to Dutch
        message = messages.get(resolved_locale) or messages.get(DEFAULT_LOCALE, "")
        if message:
            return message

    # Unknown error key — return generic fallback in Dutch
    return _UNKNOWN_ERROR_MESSAGES.get(DEFAULT_LOCALE, "Er is een fout opgetreden")
