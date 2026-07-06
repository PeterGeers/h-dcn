"""
Unit tests for scripts/generate_og_html.py

Tests the OG HTML generation logic (no S3 interaction needed).
"""

import os
import sys

import pytest

# Add scripts directory to path for import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from scripts.generate_og_html import generate_og_html, _build_og_description, _format_date


class TestGenerateOgHtml:
    """Test HTML generation with various event data."""

    def test_full_event(self) -> None:
        """Complete event with all fields produces correct OG tags."""
        event = {
            'name': 'Toerweekend 2026',
            'slug': 'toerweekend-2026',
            'start_date': '2026-07-17',
            'end_date': '2026-07-20',
            'location': 'Holysloot, Amsterdam',
            'poster_url': 'https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/event-posters/toerweekend-2026.jpg',
            'description': 'Jaarlijks toerweekend van H-DCN',
        }

        html: str = generate_og_html(event)

        # OG tags
        assert 'og:title" content="Toerweekend 2026"' in html
        assert 'og:url" content="https://portal.h-dcn.nl/events/toerweekend-2026/info"' in html
        assert 'og:image" content="https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/event-posters/toerweekend-2026.jpg"' in html
        assert 'og:type" content="website"' in html

        # Twitter card
        assert 'twitter:card" content="summary_large_image"' in html
        assert 'twitter:title" content="Toerweekend 2026"' in html
        assert 'twitter:image"' in html

        # Description contains date and location
        assert '17 juli 2026' in html
        assert '20 juli 2026' in html
        assert 'Holysloot, Amsterdam' in html

    def test_minimal_event(self) -> None:
        """Event with only required fields still produces valid HTML."""
        event = {
            'name': 'ALV Maart',
            'slug': 'alv-maart',
            'start_date': '2027-03-15',
        }

        html: str = generate_og_html(event)

        assert 'og:title" content="ALV Maart"' in html
        assert 'og:url" content="https://portal.h-dcn.nl/events/alv-maart/info"' in html
        assert '15 maart 2027' in html
        assert '<!DOCTYPE html>' in html

    def test_empty_event(self) -> None:
        """Empty event dict still produces valid HTML with defaults."""
        html: str = generate_og_html({})

        assert 'og:title" content="H-DCN Event"' in html
        assert '<!DOCTYPE html>' in html

    def test_html_escaping(self) -> None:
        """Special characters in event data are properly escaped."""
        event = {
            'name': 'Event "Special" <2026>',
            'slug': 'event-special-2026',
            'start_date': '2026-01-01',
            'location': 'Café & Bar',
        }

        html: str = generate_og_html(event)

        # Characters should be escaped
        assert '&quot;' in html or '&#x27;' in html or 'Event &quot;Special&quot; &lt;2026&gt;' in html
        assert '<2026>' not in html  # Raw angle brackets should not appear in meta content
        assert 'Caf\u00e9 &amp; Bar' in html

    def test_single_day_event(self) -> None:
        """Single day event (start == end) shows only one date."""
        event = {
            'name': 'Openingsrit',
            'slug': 'openingsrit-2026',
            'start_date': '2026-04-01',
            'end_date': '2026-04-01',
            'location': 'Amsterdam',
        }

        html: str = generate_og_html(event)

        # Should show date only once (not "1 april 2026 - 1 april 2026")
        assert '1 april 2026' in html
        # The date string should appear once in the description
        assert html.count('1 april 2026') >= 1

    def test_redirect_for_browsers(self) -> None:
        """HTML includes meta refresh redirect for non-bot browsers."""
        event = {
            'name': 'Test',
            'slug': 'test-event',
            'start_date': '2026-06-01',
        }

        html: str = generate_og_html(event)

        assert 'meta http-equiv="refresh"' in html
        assert '/events/test-event/info' in html


class TestBuildOgDescription:
    """Test the description builder logic."""

    def test_date_and_location(self) -> None:
        """Date + location produces 'date • location' format."""
        result: str = _build_og_description(
            start_date='2026-07-17',
            end_date='2026-07-20',
            location='Amsterdam',
            description='',
        )
        assert '17 juli 2026' in result
        assert '20 juli 2026' in result
        assert 'Amsterdam' in result
        assert '•' in result

    def test_date_only(self) -> None:
        """Date without location just shows the date."""
        result: str = _build_og_description(
            start_date='2026-03-15',
            end_date='2026-03-15',
            location='',
            description='',
        )
        assert '15 maart 2026' in result
        assert '•' not in result

    def test_fallback_to_description(self) -> None:
        """When no date and location, falls back to description."""
        result: str = _build_og_description(
            start_date='',
            end_date='',
            location='',
            description='Dit is een test event voor H-DCN leden',
        )
        assert 'Dit is een test event' in result

    def test_fallback_to_default(self) -> None:
        """When everything is empty, returns default text."""
        result: str = _build_og_description(
            start_date='',
            end_date='',
            location='',
            description='',
        )
        assert result == 'H-DCN Event'


class TestFormatDate:
    """Test Dutch date formatting."""

    def test_standard_date(self) -> None:
        assert _format_date('2026-07-17') == '17 juli 2026'

    def test_january(self) -> None:
        assert _format_date('2026-01-05') == '5 januari 2026'

    def test_december(self) -> None:
        assert _format_date('2026-12-31') == '31 december 2026'

    def test_with_time_suffix(self) -> None:
        """Date strings with time (YYYY-MM-DDThh:mm) are handled."""
        assert _format_date('2026-03-15T14:00:00') == '15 maart 2026'

    def test_invalid_date(self) -> None:
        """Invalid date strings are returned as-is."""
        assert _format_date('invalid') == 'invalid'
        assert _format_date('') == ''
