"""
Unit tests for PDF locale integration and additional error response localization.

Tests that the order confirmation PDF generates with locale-correct text,
and validates fallback behavior for missing/invalid locales.

Requirements validated: 6.2, 8.1, 8.4
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# Add layers to path for shared module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python'))

# Add handler to path for PDF generation imports
_pdf_handler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_order_pdf'))
if _pdf_handler_path not in sys.path:
    sys.path.insert(0, _pdf_handler_path)

from shared.i18n.pdf_translations import get_pdf_text, format_date_for_locale, format_currency_for_locale
from shared.i18n.locale_resolver import resolve_member_locale
from shared.auth_utils import create_error_response


@pytest.fixture(autouse=True)
def _ensure_pdf_app_module():
    """Ensure the 'app' module points to generate_order_pdf/app.py."""
    _abs_pdf_handler_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'generate_order_pdf'))
    # Always remove cached app to force reimport from the correct path
    if 'app' in sys.modules:
        del sys.modules['app']
    # Ensure generate_order_pdf path is at the front of sys.path
    if _abs_pdf_handler_path in sys.path:
        sys.path.remove(_abs_pdf_handler_path)
    sys.path.insert(0, _abs_pdf_handler_path)
    yield
    # Cleanup — remove handler path and clear module cache
    if _abs_pdf_handler_path in sys.path:
        sys.path.remove(_abs_pdf_handler_path)
    if 'app' in sys.modules:
        del sys.modules['app']


class TestPdfGeneratesWithCorrectLocaleTranslations:
    """Test PDF renders with correct locale-specific translations.

    Validates: Requirement 8.1 - PDF uses member's preferred_language
    Validates: Requirement 8.4 - Fallback to Dutch for invalid/missing locale
    """

    def _make_order(self, **overrides):
        """Create a sample order dict for testing."""
        order = {
            'order_id': 'ORD-2025-001',
            'timestamp': '2025-01-15T14:30:00Z',
            'customer_info': {
                'name': 'Jan de Vries',
                'straat': 'Hoofdstraat 1',
                'postcode': '1234 AB',
                'woonplaats': 'Amsterdam',
                'email': 'jan@example.com',
            },
            'items': [
                {'name': 'H-DCN T-Shirt', 'selectedOption': 'XL', 'quantity': 2, 'price': 25.00},
                {'name': 'Pet', 'selectedOption': '-', 'quantity': 1, 'price': 15.00},
            ],
            'subtotal_amount': '65.00',
            'total_amount': '65.00',
            'member_id': 'member-123',
        }
        order.update(overrides)
        return order

    def test_dutch_pdf_contains_dutch_title(self):
        """PDF rendered with locale='nl' contains Dutch document title."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='nl')
        assert 'Orderbevestiging' in html

    def test_english_pdf_contains_english_title(self):
        """PDF rendered with locale='en' contains English document title."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='en')
        assert 'Order Confirmation' in html

    def test_french_pdf_contains_french_title(self):
        """PDF rendered with locale='fr' contains French document title."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='fr')
        assert 'Confirmation de commande' in html

    def test_german_pdf_contains_german_title(self):
        """PDF rendered with locale='de' contains German document title."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='de')
        assert 'Auftragsbestätigung' in html

    def test_pdf_html_lang_attribute_matches_locale(self):
        """PDF HTML element has lang attribute matching the requested locale."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='sv')
        assert 'lang="sv"' in html

    def test_pdf_table_headers_localized(self):
        """PDF product table headers match requested locale."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='en')
        assert 'Product' in html
        assert 'Quantity' in html
        assert 'Unit Price' in html
        assert 'Total' in html

    def test_pdf_table_headers_localized_italian(self):
        """PDF product table headers render in Italian for locale='it'."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='it')
        assert 'Prodotto' in html
        assert 'Quantità' in html or 'Quantit' in html
        assert 'Prezzo unitario' in html

    def test_pdf_status_localized(self):
        """PDF status text renders in the correct locale."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='es')
        assert 'Pagado' in html  # Spanish for "Paid"

    def test_pdf_address_labels_localized(self):
        """PDF address section labels render in the correct locale."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='de')
        assert 'Rechnungsadresse' in html
        assert 'Lieferadresse' in html

    def test_pdf_totals_labels_localized(self):
        """PDF totals section labels render in the correct locale."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='fr')
        assert 'Sous-total' in html
        assert 'Total payé' in html


class TestPdfFallbackToDutchForInvalidLocale:
    """Test PDF generation falls back to Dutch for invalid/missing locale.

    Validates: Requirement 8.4
    """

    def _make_order(self):
        return {
            'order_id': 'ORD-2025-002',
            'timestamp': '2025-03-20T10:00:00Z',
            'customer_info': {'name': 'Test User'},
            'items': [{'name': 'Widget', 'selectedOption': '-', 'quantity': 1, 'price': 10.00}],
            'subtotal_amount': '10.00',
            'total_amount': '10.00',
        }

    def test_invalid_locale_falls_back_to_dutch(self):
        """PDF with invalid locale renders Dutch text."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='xx')
        assert 'Orderbevestiging' in html

    def test_empty_locale_falls_back_to_dutch(self):
        """PDF with empty locale renders Dutch text."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='')
        assert 'Orderbevestiging' in html

    def test_none_locale_falls_back_to_dutch(self):
        """PDF with None locale renders Dutch text (via resolve_member_locale)."""
        locale = resolve_member_locale(None)
        assert locale == 'nl'

    def test_unsupported_locale_code_falls_back_to_dutch(self):
        """PDF with unsupported locale (e.g. 'zh') renders Dutch text."""
        from app import render_order_html
        order = self._make_order()
        html = render_order_html(order, logo_data_uri=None, locale='zh')
        assert 'Orderbevestiging' in html


class TestPdfDateFormatting:
    """Test PDF date formatting per locale.

    Validates: Requirement 8.3 (locale-aware date formatting in PDF)
    """

    def test_dutch_date_format(self):
        """Dutch date format: '15 januari 2025'."""
        dt = datetime(2025, 1, 15)
        result = format_date_for_locale(dt, 'nl')
        assert result == '15 januari 2025'

    def test_english_date_format(self):
        """English date format: '15 January 2025'."""
        dt = datetime(2025, 1, 15)
        result = format_date_for_locale(dt, 'en')
        assert result == '15 January 2025'

    def test_german_date_format(self):
        """German date format uses period: '15. Januar 2025'."""
        dt = datetime(2025, 1, 15)
        result = format_date_for_locale(dt, 'de')
        assert result == '15. Januar 2025'

    def test_spanish_date_format(self):
        """Spanish date format: '15 de enero de 2025'."""
        dt = datetime(2025, 1, 15)
        result = format_date_for_locale(dt, 'es')
        assert result == '15 de enero de 2025'

    def test_invalid_locale_date_format_falls_back_to_dutch(self):
        """Invalid locale falls back to Dutch date format."""
        dt = datetime(2025, 6, 20)
        result = format_date_for_locale(dt, 'xyz')
        assert result == '20 juni 2025'


class TestPdfCurrencyFormatting:
    """Test PDF currency formatting per locale.

    Validates: Requirement 8.3 (locale-aware currency formatting in PDF)
    """

    def test_dutch_currency_format(self):
        """Dutch currency: '€ 1.234,56' (non-breaking space after €)."""
        result = format_currency_for_locale(1234.56, 'nl')
        assert '€' in result
        assert '1.234' in result
        assert ',56' in result

    def test_english_currency_format(self):
        """English currency: '€1,234.56' (no space after €)."""
        result = format_currency_for_locale(1234.56, 'en')
        assert '€' in result
        assert '1,234' in result
        assert '.56' in result

    def test_french_currency_format(self):
        """French currency: symbol after amount."""
        result = format_currency_for_locale(1234.56, 'fr')
        assert '€' in result
        assert ',56' in result
        # French puts € after the number
        euro_pos = result.index('€')
        digit_pos = result.index('1')
        assert euro_pos > digit_pos

    def test_invalid_locale_currency_falls_back_to_dutch(self):
        """Invalid locale falls back to Dutch currency format."""
        result = format_currency_for_locale(99.99, 'invalid')
        assert '€' in result
        assert '99,99' in result


class TestPdfResolvesMemberLocale:
    """Test that PDF generation resolves locale from member's preferred_language.

    Validates: Requirement 8.1 - PDF uses member's preferred_language from Members table.
    """

    def test_resolve_member_locale_valid(self):
        """resolve_member_locale returns valid stored preference."""
        assert resolve_member_locale('en') == 'en'
        assert resolve_member_locale('fr') == 'fr'
        assert resolve_member_locale('de') == 'de'

    def test_resolve_member_locale_null_returns_dutch(self):
        """resolve_member_locale returns Dutch for None."""
        assert resolve_member_locale(None) == 'nl'

    def test_resolve_member_locale_empty_returns_dutch(self):
        """resolve_member_locale returns Dutch for empty string."""
        assert resolve_member_locale('') == 'nl'

    def test_resolve_member_locale_invalid_returns_dutch(self):
        """resolve_member_locale returns Dutch for unsupported locale."""
        assert resolve_member_locale('zh') == 'nl'
        assert resolve_member_locale('jp') == 'nl'

    def test_resolve_member_locale_case_insensitive(self):
        """resolve_member_locale handles uppercase input."""
        assert resolve_member_locale('EN') == 'en'
        assert resolve_member_locale('Fr') == 'fr'


class TestErrorResponseContainsBothKeyAndMessage:
    """Test error response includes both error_key and localized message.

    Validates: Requirement 6.2
    Extends existing tests in test_localized_error_responses.py with additional
    locale coverage and edge cases.
    """

    def test_all_supported_locales_return_localized_message(self):
        """Error response provides localized message for each supported locale."""
        supported_locales = ['nl', 'en', 'fr', 'de', 'sv', 'da', 'it', 'es']
        for locale in supported_locales:
            response = create_error_response(403, 'Fallback', error_key='forbidden', locale=locale)
            body = json.loads(response['body'])
            assert 'error_key' in body, f"Missing error_key for locale {locale}"
            assert 'message' in body, f"Missing message for locale {locale}"
            assert body['error_key'] == 'forbidden'
            assert body['message'] != '', f"Empty message for locale {locale}"

    def test_error_key_is_stable_across_locales(self):
        """error_key field is the same regardless of locale."""
        responses = {}
        for locale in ['nl', 'en', 'fr', 'de']:
            resp = create_error_response(404, 'Not found', error_key='not_found', locale=locale)
            responses[locale] = json.loads(resp['body'])

        keys = [r['error_key'] for r in responses.values()]
        assert all(k == 'not_found' for k in keys)

    def test_message_differs_per_locale(self):
        """Localized message is different for different locales."""
        resp_nl = create_error_response(403, 'X', error_key='forbidden', locale='nl')
        resp_en = create_error_response(403, 'X', error_key='forbidden', locale='en')
        body_nl = json.loads(resp_nl['body'])
        body_en = json.loads(resp_en['body'])
        assert body_nl['message'] != body_en['message']

    def test_unknown_error_key_returns_dutch_fallback_message(self):
        """Unknown error_key still returns a message (generic Dutch fallback)."""
        response = create_error_response(500, 'Error', error_key='totally_unknown_key', locale='en')
        body = json.loads(response['body'])
        assert 'error_key' in body
        assert 'message' in body
        assert body['message'] != ''
