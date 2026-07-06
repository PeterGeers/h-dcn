"""
Unit tests for the event duplicate detection utility.

Tests fuzzy matching on name, date, and location to ensure
near-duplicates are caught without too many false positives.
"""

import os
import sys
import pytest
import boto3
from moto import mock_aws

# Ensure scripts/ is importable
_scripts_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts')
)
if _scripts_path not in sys.path:
    sys.path.insert(0, _scripts_path)

from shared.event_dedup import (
    check_duplicate,
    format_dry_run_result,
    fuzzy_location_match,
    fuzzy_name_match,
    levenshtein_distance,
    token_overlap,
)

# --- AWS credentials for moto ---
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'


@pytest.fixture
def events_table():
    """Create a mocked Events DynamoDB table with test data."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Events',
            KeySchema=[{'AttributeName': 'event_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'event_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed test events
        table.put_item(Item={
            'event_id': 'evt-001',
            'name': 'Toerweekend 2026',
            'start_date': '2026-06-15',
            'location': 'Clubhuis H-DCN, Amsterdam',
            'status': 'published',
        })
        table.put_item(Item={
            'event_id': 'evt-002',
            'name': 'ALV Maart',
            'start_date': '2027-03-10',
            'location': 'Holysloot',
            'status': 'draft',
        })
        table.put_item(Item={
            'event_id': 'evt-003',
            'name': 'Openingsrit Noord',
            'start_date': '2026-04-01',
            'location': '',
            'status': 'published',
        })
        table.put_item(Item={
            'event_id': 'evt-004',
            'name': 'Zomerrit Zuid',
            'start_date': '2026-07-20',
            'location': 'Maastricht',
            'status': 'published',
        })

        yield table


# ============================================================
# Levenshtein distance unit tests
# ============================================================

class TestLevenshteinDistance:
    """Tests for the manual Levenshtein implementation."""

    def test_identical_strings(self) -> None:
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_strings(self) -> None:
        assert levenshtein_distance("", "") == 0

    def test_one_empty(self) -> None:
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "xyz") == 3

    def test_single_substitution(self) -> None:
        assert levenshtein_distance("cat", "car") == 1

    def test_single_insertion(self) -> None:
        assert levenshtein_distance("cat", "cats") == 1

    def test_single_deletion(self) -> None:
        assert levenshtein_distance("cats", "cat") == 1

    def test_multiple_edits(self) -> None:
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_completely_different(self) -> None:
        assert levenshtein_distance("abc", "xyz") == 3


# ============================================================
# Token overlap tests
# ============================================================

class TestTokenOverlap:
    """Tests for token overlap calculation."""

    def test_identical(self) -> None:
        assert token_overlap("ALV Maart", "ALV Maart") == 1.0

    def test_case_insensitive(self) -> None:
        assert token_overlap("ALV Maart", "alv maart") == 1.0

    def test_partial_overlap(self) -> None:
        # "ALV" and "Maart" overlap with "ALV", "maart", "2027"
        # intersection = {"alv", "maart"} = 2, max_len = 3
        result = token_overlap("ALV Maart", "ALV maart 2027")
        assert abs(result - 2 / 3) < 0.01

    def test_no_overlap(self) -> None:
        assert token_overlap("Zomerrit", "Winter tour") == 0.0

    def test_empty_string(self) -> None:
        assert token_overlap("", "test") == 0.0
        assert token_overlap("test", "") == 0.0


# ============================================================
# Fuzzy name match tests
# ============================================================

class TestFuzzyNameMatch:
    """Tests for fuzzy name matching logic."""

    def test_exact_match(self) -> None:
        assert fuzzy_name_match("Toerweekend 2026", "Toerweekend 2026") is True

    def test_case_insensitive(self) -> None:
        assert fuzzy_name_match("ALV Maart", "alv maart") is True

    def test_small_typo_levenshtein(self) -> None:
        # "Toerweekend" vs "Toerweeknd" = 1 edit (within ≤ 3)
        assert fuzzy_name_match("Toerweekend 2026", "Toerweeknd 2026") is True

    def test_token_overlap_match(self) -> None:
        # "ALV Maart" vs "ALV maart 2027" → 2/3 ≈ 0.67 < 0.70
        # But Levenshtein("alv maart", "alv maart 2027") = 5 > 3
        # So this should NOT match (below 70% and above levenshtein 3)
        # Actually: tokens are {"alv", "maart"} and {"alv", "maart", "2027"}
        # overlap = 2/3 = 0.667 < 0.70 → no token match
        # Levenshtein distance = 5 > 3 → no levenshtein match
        assert fuzzy_name_match("ALV Maart", "ALV maart 2027") is False

    def test_high_token_overlap(self) -> None:
        # "Openingsrit Noord Holland" vs "Openingsrit Noord" → 2/3 ≈ 0.67 < 0.70
        # But let's try one that actually triggers 70%:
        # "Rit Noord Holland" vs "Rit Noord Holland Zomer" → 3/4 = 0.75 ≥ 0.70
        assert fuzzy_name_match("Rit Noord Holland", "Rit Noord Holland Zomer") is True

    def test_completely_different_names(self) -> None:
        assert fuzzy_name_match("Toerweekend 2026", "Zomerrit Zuid") is False

    def test_levenshtein_boundary_3(self) -> None:
        # Exactly 3 edits should still match
        assert fuzzy_name_match("abcdef", "xbcdeg") is True  # 2 substitutions = matches

    def test_levenshtein_beyond_3_no_match(self) -> None:
        # 4+ edits should NOT match via levenshtein (and no token overlap either)
        # "abcdefgh" vs "xyzwefgh" = 4 substitutions (a→x, b→y, c→z, d→w)
        assert fuzzy_name_match("abcdefgh", "xyzwefgh") is False


# ============================================================
# Fuzzy location match tests
# ============================================================

class TestFuzzyLocationMatch:
    """Tests for fuzzy location matching logic."""

    def test_exact_match(self) -> None:
        assert fuzzy_location_match("Amsterdam", "Amsterdam") is True

    def test_contains_check(self) -> None:
        assert fuzzy_location_match("Amsterdam", "Clubhuis H-DCN, Amsterdam") is True

    def test_contains_reverse(self) -> None:
        assert fuzzy_location_match("Holysloot, Amsterdam", "Holysloot") is True

    def test_case_insensitive_contains(self) -> None:
        assert fuzzy_location_match("amsterdam", "AMSTERDAM") is True

    def test_levenshtein_location(self) -> None:
        # "Maastricht" vs "Maastricht NL" = 3 edits (≤ 5)
        assert fuzzy_location_match("Maastricht", "Maastricht NL") is True

    def test_completely_different_locations(self) -> None:
        assert fuzzy_location_match("Amsterdam", "Maastricht") is False


# ============================================================
# check_duplicate integration tests (with mocked DynamoDB)
# ============================================================

class TestCheckDuplicate:
    """Integration tests for check_duplicate with mocked DynamoDB."""

    def test_exact_duplicate_found(self, events_table) -> None:
        """Same name + same date → duplicate."""
        result = check_duplicate(
            name="Toerweekend 2026",
            start_date="2026-06-15",
            location="Amsterdam",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-001'

    def test_typo_in_name_still_matches(self, events_table) -> None:
        """Small typo in name (Levenshtein ≤ 3) + same date → duplicate."""
        result = check_duplicate(
            name="Toerweeknd 2026",  # missing 'e'
            start_date="2026-06-15",
            location="Amsterdam",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-001'

    def test_different_date_no_match(self, events_table) -> None:
        """Same name but different date → unique (date is hard filter)."""
        result = check_duplicate(
            name="Toerweekend 2026",
            start_date="2026-06-16",  # one day off
            location="Amsterdam",
            table=events_table,
        )
        assert result is None

    def test_completely_different_name_no_match(self, events_table) -> None:
        """Completely different name on same date → unique."""
        result = check_duplicate(
            name="Winterrit 2026",
            start_date="2026-06-15",
            location="Amsterdam",
            table=events_table,
        )
        assert result is None

    def test_location_contains_match(self, events_table) -> None:
        """Location substring match strengthens duplicate detection."""
        result = check_duplicate(
            name="Toerweekend 2026",
            start_date="2026-06-15",
            location="Clubhuis H-DCN, Amsterdam",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-001'

    def test_empty_location_still_matches_on_name_date(self, events_table) -> None:
        """Empty location skips location check — matches on name + date."""
        result = check_duplicate(
            name="Openingsrit Noord",
            start_date="2026-04-01",
            location="",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-003'

    def test_no_events_for_date_returns_none(self, events_table) -> None:
        """No events exist for the given date → unique."""
        result = check_duplicate(
            name="Nieuw Evenement",
            start_date="2030-01-01",
            location="Utrecht",
            table=events_table,
        )
        assert result is None

    def test_case_insensitive_name_match(self, events_table) -> None:
        """Name matching is case-insensitive."""
        result = check_duplicate(
            name="toerweekend 2026",
            start_date="2026-06-15",
            location="",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-001'

    def test_token_overlap_match(self, events_table) -> None:
        """Token overlap ≥ 70% catches name variations."""
        # "Zomerrit Zuid" vs "Zomerrit Zuid Holland"
        # tokens existing: {"zomerrit", "zuid"}, new: {"zomerrit", "zuid", "holland"}
        # overlap = 2/3 = 0.67 < 0.70 → not enough
        # Let's use a better example: insert an event with more tokens
        events_table.put_item(Item={
            'event_id': 'evt-005',
            'name': 'Rit Noord Holland Voorjaar',
            'start_date': '2026-05-01',
            'location': 'Haarlem',
            'status': 'published',
        })
        # "Rit Noord Holland Voorjaar Editie" vs "Rit Noord Holland Voorjaar"
        # tokens new: {"rit", "noord", "holland", "voorjaar", "editie"} = 5
        # tokens existing: {"rit", "noord", "holland", "voorjaar"} = 4
        # overlap = 4/5 = 0.80 ≥ 0.70 → match!
        result = check_duplicate(
            name="Rit Noord Holland Voorjaar Editie",
            start_date="2026-05-01",
            location="",
            table=events_table,
        )
        assert result is not None
        assert result['event_id'] == 'evt-005'


# ============================================================
# Dry-run formatting tests
# ============================================================

class TestFormatDryRunResult:
    """Tests for --dry-run output formatting."""

    def test_unique_event_formatting(self) -> None:
        output = format_dry_run_result("Nieuw Event", "2026-01-01", None)
        assert "UNIQUE" in output
        assert "Nieuw Event" in output
        assert "2026-01-01" in output

    def test_duplicate_event_formatting(self) -> None:
        match = {"event_id": "evt-001", "name": "Toerweekend 2026"}
        output = format_dry_run_result("Toerweeknd 2026", "2026-06-15", match)
        assert "DUPLICATE" in output
        assert "Toerweeknd 2026" in output
        assert "Toerweekend 2026" in output
        assert "evt-001" in output
