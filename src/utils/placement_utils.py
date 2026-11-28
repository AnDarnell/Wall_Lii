"""Utility functions for estimating player placements based on MMR changes."""

from datetime import datetime, timezone
from typing import List, Optional, Sequence
import math

from config import (
    RATING_CAP_MAX,
    RATING_CAP_SEASON_START,
    RATING_CAP_START,
    RATING_CAP_STEP_PER_DAY,
)


def _to_utc(timestamp) -> datetime:
    """
    Normalize timestamps to an aware UTC datetime. (Brugdar)

    Missing/invalid timestamp -> fall back to the current UTC time. (Brugdar)
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            timestamp = None

    if not isinstance(timestamp, datetime):
        return datetime.now(timezone.utc)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def get_rating_cap(timestamp=None) -> int:
    """
    Dynamic rating cap. Grows in whole steps per full day.

    Args:
        timestamp: Optional time the rating was observed - default: current UTC time. (Brugdar)

    Returns:
        The rating cap (int) at that time. (Brugdar)
    """
    days = max(0, (_to_utc(timestamp) - RATING_CAP_SEASON_START).days)
    return min(RATING_CAP_MAX, RATING_CAP_START + RATING_CAP_STEP_PER_DAY * days)


def estimate_placement(start: float, end: float, timestamp=None) -> dict:
    """
    Estimate most likely placement given start and end MMR.

    Args:
        start: Starting MMR value
        end: Ending MMR value
        timestamp: Optional time the rating was observed - default: current UTC time. (Brugdar)

    Returns:
        Dictionary with 'placement' (number) and 'delta' (number) keys
    """
    gain = end - start
    rating_cap = get_rating_cap(timestamp)

    # Possible placements
    placements = [1, 2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8]

    # Calculate dexAvg - matches PostgreSQL function exactly
    if start < 8200:
        dex_avg = start
    else:
        dex_avg = start - 0.85 * (start - 8500)

    # Find placement with smallest delta
    best_placement = placements[0]
    best_delta = float("inf")

    for p in placements:
        # avgOpp-formula
        avg_opp = start - 148.1181435 * (100 - ((p - 1) * (200.0 / 7.0) + gain))
<<<<<<< HEAD
        if avg_opp > rating_cap:
=======
        if avg_opp > 12500:
>>>>>>> upstream/main
            continue

        delta = abs(dex_avg - avg_opp)

        if delta < best_delta:
            best_delta = delta
            best_placement = p

    return {"placement": best_placement, "delta": best_delta}


def calculate_placements(
    ratings: List[float], timestamps: Optional[Sequence] = None
) -> List[float]:
    """
    Calculate placements for an array of ratings.

    Args:
        ratings: Array of rating values in chronological order
        timestamps: Optional snapshot times, one per rating - default: current UTC time. (Brugdar)

    Returns:
        Array of placements (X ratings returns X-1 placements)
    """
    if len(ratings) < 2:
        return []

    use_timestamps = timestamps is not None and len(timestamps) == len(ratings)
    placements = []

    for i in range(len(ratings) - 1):
        start = ratings[i]
        end = ratings[i + 1]
        # The snapshot that ends the change decides the rating cap (Brugdar)
        ts = timestamps[i + 1] if use_timestamps else None 
        result = estimate_placement(start, end, ts)
        placements.append(result["placement"])

    return placements


def calculate_average_placement(
    ratings: List[float], timestamps: Optional[Sequence] = None
) -> float:
    """
    Calculate the average placement from an array of ratings.

    Args:
        ratings: Array of rating values in chronological order
        timestamps: Optional snapshot times, one per rating - default: current UTC time. (Brugdar)

    Returns:
        Average placement (returns NaN if fewer than 2 ratings)
    """
    placements = calculate_placements(ratings, timestamps)

    if len(placements) == 0:
        return float("nan")

    return sum(placements) / len(placements)


def calculate_placements_with_average(
    ratings: List[float],
    precision: int = 2,
    timestamps: Optional[Sequence] = None,
) -> dict:
    """
    Calculate both placements array and average placement.
    Useful when you need both values without calculating twice.

    Args:
        ratings: Array of rating values in chronological order
        precision: Number of decimal places for average rounding (default: 2)
        timestamps: Optional snapshot times, one per rating - default: current UTC time. (Brugdar)

    Returns:
        Dictionary with 'placements' (list) and 'average' (float) keys
    """
    placements = calculate_placements(ratings, timestamps)

    if len(placements) == 0:
        average = float("nan")
    else:
        average = sum(placements) / len(placements)

    # Round average if it's a valid number
    if isinstance(average, float) and not math.isnan(average):
        average = round(average, precision)

    return {"placements": placements, "average": average}