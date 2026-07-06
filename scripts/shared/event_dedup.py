"""
Duplicate detection utility for H-DCN event imports.

Provides fuzzy matching on name + date + location to prevent
near-duplicate events from being inserted into the Events table.
"""

from __future__ import annotations

from typing import Any


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row: list[int] = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row: list[int] = [i + 1]
        for j, c2 in enumerate(s2):
            # Insertions, deletions, substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (0 if c1 == c2 else 1)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def token_overlap(name_a: str, name_b: str) -> float:
    """
    Compute token overlap ratio between two names.

    Splits on whitespace, compares lowercase tokens.
    Returns the fraction of overlapping tokens relative to the
    larger token set (intersection / max(len_a, len_b)).
    """
    tokens_a: set[str] = set(name_a.lower().split())
    tokens_b: set[str] = set(name_b.lower().split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection: int = len(tokens_a & tokens_b)
    max_len: int = max(len(tokens_a), len(tokens_b))

    return intersection / max_len


def fuzzy_name_match(name_a: str, name_b: str) -> bool:
    """
    Check if two event names are a fuzzy match.

    Match criteria (case-insensitive):
    - Levenshtein distance ≤ 3, OR
    - Token overlap ≥ 70%
    """
    a_lower: str = name_a.lower().strip()
    b_lower: str = name_b.lower().strip()

    # Exact match (fast path)
    if a_lower == b_lower:
        return True

    # Levenshtein distance ≤ 3
    if levenshtein_distance(a_lower, b_lower) <= 3:
        return True

    # Token overlap ≥ 70%
    if token_overlap(name_a, name_b) >= 0.70:
        return True

    return False


def fuzzy_location_match(loc_a: str, loc_b: str) -> bool:
    """
    Check if two locations are a fuzzy match.

    Match criteria (case-insensitive):
    - One contains the other (substring check), OR
    - Levenshtein distance ≤ 5
    """
    a_lower: str = loc_a.lower().strip()
    b_lower: str = loc_b.lower().strip()

    # Exact match (fast path)
    if a_lower == b_lower:
        return True

    # Contains check (one contains the other)
    if a_lower in b_lower or b_lower in a_lower:
        return True

    # Levenshtein distance ≤ 5
    if levenshtein_distance(a_lower, b_lower) <= 5:
        return True

    return False


def check_duplicate(
    name: str,
    start_date: str,
    location: str,
    table: Any,
) -> dict[str, Any] | None:
    """
    Fuzzy duplicate detection for events.

    Scans the Events DynamoDB table for events with the same start_date,
    then applies fuzzy matching on name and location.

    Args:
        name: Event name to check.
        start_date: Event start date (YYYY-MM-DD format) — exact match required.
        location: Event location — fuzzy match (empty string skips location check).
        table: boto3 DynamoDB Table resource.

    Returns:
        The existing event dict if a probable duplicate is found, None if unique.

    Match strategy:
        exact_date AND (fuzzy_name OR (fuzzy_name_partial AND fuzzy_location))

    Since fuzzy_name already covers partial cases via token overlap,
    the effective logic is: exact_date AND fuzzy_name.
    When location is provided and name is borderline, location strengthens confidence.
    """
    # Step 1: Scan for events with exact date match
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "#sd = :date_val",
        "ExpressionAttributeNames": {"#sd": "start_date"},
        "ExpressionAttributeValues": {":date_val": start_date},
    }

    candidates: list[dict[str, Any]] = []
    response: dict[str, Any] = table.scan(**scan_kwargs)
    candidates.extend(response.get("Items", []))

    # Handle pagination
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        candidates.extend(response.get("Items", []))

    # Step 2: Apply fuzzy matching on candidates
    for event in candidates:
        existing_name: str = event.get("name", "")

        if fuzzy_name_match(name, existing_name):
            # Name matches — if location is provided, it strengthens confidence
            # but a name match alone is sufficient for duplicate detection
            if location and event.get("location"):
                # Both have location: check if they also match on location
                if fuzzy_location_match(location, event["location"]):
                    return event
                # Location mismatch with same date + similar name is still suspicious
                # but we trust the name match (Levenshtein ≤ 3 or 70% overlap is strong)
                return event
            else:
                # Empty location on either side: match on name + date only
                return event

    return None


def format_dry_run_result(
    event_name: str,
    start_date: str,
    match: dict[str, Any] | None,
) -> str:
    """
    Format duplicate check result for --dry-run output.

    Args:
        event_name: Name of the event being checked.
        start_date: Date of the event being checked.
        match: The matched event dict, or None if unique.

    Returns:
        Formatted string for console output.
    """
    if match is None:
        return f"  ✓ UNIQUE: '{event_name}' ({start_date})"

    existing_name: str = match.get("name", "?")
    existing_id: str = match.get("event_id", "?")
    return (
        f"  ⚠ DUPLICATE: '{event_name}' ({start_date}) "
        f"matches existing '{existing_name}' (id: {existing_id})"
    )
