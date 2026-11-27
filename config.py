# config.py
import os
from datetime import datetime, timezone

SEASON = int(os.environ.get("CURRENT_SEASON", "19"))
TABLE_SUFFIX = f"_season{SEASON}"

TABLES = {
    "current_leaderboard": f"current_leaderboard{TABLE_SUFFIX}",
    "leaderboard_snapshots": f"leaderboard_snapshots{TABLE_SUFFIX}",
    "milestone_tracking": f"milestone_tracking{TABLE_SUFFIX}",
}

# New normalized table structure
NORMALIZED_TABLES = {
    "daily_leaderboard_stats": "daily_leaderboard_stats",
    "leaderboard_snapshots": "leaderboard_snapshots",
    "players": "players",
    "milestone_tracking": "milestone_tracking",
}

# Rating cap configurations (Brugdar)
RATING_CAP_SEASON_START = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
RATING_CAP_START = 8500
RATING_CAP_STEP_PER_DAY = 50
RATING_CAP_MAX = 12500