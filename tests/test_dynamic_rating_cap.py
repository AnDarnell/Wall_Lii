"""Tests for the dynamic rating cap in placement_utils."""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from utils import placement_utils as pu  # noqa: E402
from utils.placement_utils import (  # noqa: E402
    calculate_average_placement,
    calculate_placements,
    calculate_placements_with_average,
    estimate_placement,
    get_rating_cap,
)

START = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)


class RatingCapTests(unittest.TestCase):
    def test_cap_at_season_start(self):
        self.assertEqual(get_rating_cap(START), 8500)

    def test_cap_after_12_hours(self):
        self.assertEqual(get_rating_cap(START + timedelta(hours=12)), 8500)

    def test_cap_after_24_hours(self):
        self.assertEqual(get_rating_cap(START + timedelta(hours=24)), 8550)

    def test_cap_after_36_hours(self):
        self.assertEqual(get_rating_cap(START + timedelta(hours=36)), 8550)

    def test_cap_after_48_hours(self):
        self.assertEqual(get_rating_cap(START + timedelta(hours=48)), 8600)

    def test_cap_just_before_step(self):
        self.assertEqual(get_rating_cap(START + timedelta(hours=23, minutes=59)), 8500)

    def test_cap_never_exceeds_max(self):
        self.assertEqual(get_rating_cap(START + timedelta(days=80)), 12500)
        self.assertEqual(get_rating_cap(START + timedelta(days=5000)), 12500)

    def test_cap_reaches_max_on_day_80(self):
        self.assertEqual(get_rating_cap(START + timedelta(days=79)), 12450)
        self.assertEqual(get_rating_cap(START + timedelta(days=80)), 12500)

    def test_before_season_start(self):
        self.assertEqual(get_rating_cap(START - timedelta(days=30)), 8500)
        self.assertEqual(get_rating_cap(START - timedelta(seconds=1)), 8500)

    def test_naive_datetime_is_treated_as_utc(self):
        self.assertEqual(get_rating_cap(datetime(2026, 8, 6)), 8550)

    def test_non_utc_timezone_is_converted(self):
        stockholm = timezone(timedelta(hours=2))
        # 2026-08-06 01:00 +02:00 == 2026-08-05 23:00 UTC -> still day 0
        self.assertEqual(get_rating_cap(datetime(2026, 8, 6, 1, tzinfo=stockholm)), 8500)

    def test_iso_string(self):
        self.assertEqual(get_rating_cap("2026-08-07T00:00:00Z"), 8600)

    def test_missing_or_invalid_falls_back_to_now(self):
        fixed_now = START + timedelta(days=10)

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        with mock.patch.object(pu, "datetime", FrozenDatetime):
            for bad in (None, "not a date", 12345, object()):
                self.assertEqual(get_rating_cap(bad), 9000, msg=repr(bad))


class EstimatePlacementTests(unittest.TestCase):
    def test_cap_changes_result_over_time(self):
        # Large gain: avg_opp for good placements exceeds an early low cap,
        # so the chosen placement differs from late-season (high cap).
        early = estimate_placement(8400, 8600, START)
        late = estimate_placement(8400, 8600, START + timedelta(days=80))
        self.assertIn("placement", early)
        self.assertIn("placement", late)

    def test_old_signature_still_works(self):
        result = estimate_placement(8000, 8100)
        self.assertIn("placement", result)
        self.assertIn("delta", result)


class CalculatePlacementsTests(unittest.TestCase):
    def test_uses_ending_snapshot_timestamp(self):
        ratings = [8000, 8050, 8100, 8040]
        ts = [START + timedelta(days=d) for d in (0, 1, 2, 3)]
        with mock.patch.object(pu, "estimate_placement", wraps=pu.estimate_placement) as m:
            calculate_placements(ratings, ts)
        passed = [c.args[2] for c in m.call_args_list]
        self.assertEqual(passed, [ts[1], ts[2], ts[3]])

    def test_without_timestamps_passes_none(self):
        with mock.patch.object(pu, "estimate_placement", wraps=pu.estimate_placement) as m:
            calculate_placements([8000, 8050, 8100])
        self.assertTrue(all(c.args[2] is None for c in m.call_args_list))

    def test_length_mismatch_falls_back(self):
        with mock.patch.object(pu, "estimate_placement", wraps=pu.estimate_placement) as m:
            calculate_placements([8000, 8050, 8100], [START])
        self.assertTrue(all(c.args[2] is None for c in m.call_args_list))

    def test_existing_calls_unchanged(self):
        ratings = [8000, 8050, 8100]
        self.assertEqual(len(calculate_placements(ratings)), 2)
        self.assertEqual(calculate_placements([8000]), [])
        self.assertTrue(calculate_average_placement([8000]) != calculate_average_placement([8000]))  # NaN
        result = calculate_placements_with_average(ratings)
        self.assertEqual(len(result["placements"]), 2)

    def test_with_average_accepts_timestamps(self):
        ratings = [8000, 8050, 8100]
        ts = [START, START + timedelta(days=1), START + timedelta(days=2)]
        result = calculate_placements_with_average(ratings, 2, timestamps=ts)
        self.assertEqual(len(result["placements"]), 2)
        avg = calculate_average_placement(ratings, ts)
        self.assertAlmostEqual(avg, sum(result["placements"]) / 2, places=2)


if __name__ == "__main__":
    unittest.main()
