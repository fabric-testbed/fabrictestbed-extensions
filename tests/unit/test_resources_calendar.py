"""
Unit tests for FablibManager.resources_calendar().
"""

import datetime
import os
import pathlib
import unittest
from unittest.mock import MagicMock, patch

from fabrictestbed_extensions.fablib.fablib import FablibManager

# A minimal calendar response that Utils.show_calendar can process
EMPTY_CALENDAR = {
    "data": [],
    "interval": "day",
    "query_start": "",
    "query_end": "",
    "total": 0,
}

SAMPLE_CALENDAR = {
    "data": [
        {
            "start": "2025-07-01T00:00:00+00:00",
            "end": "2025-07-02T00:00:00+00:00",
            "sites": [
                {
                    "name": "RENC",
                    "cores_available": 100,
                    "cores_capacity": 128,
                    "ram_available": 400,
                    "ram_capacity": 512,
                    "disk_available": 5000,
                    "disk_capacity": 10000,
                    "components": {},
                }
            ],
            "hosts": [
                {
                    "name": "renc-w1.fabric-testbed.net",
                    "cores_available": 32,
                    "cores_capacity": 64,
                    "ram_available": 200,
                    "ram_capacity": 256,
                    "disk_available": 2000,
                    "disk_capacity": 5000,
                    "components": {
                        "GPU Tesla T4": {"available": 2, "capacity": 4},
                    },
                }
            ],
            "links": [],
            "facility_ports": [],
        }
    ],
    "interval": "day",
    "query_start": "2025-07-01T00:00:00+00:00",
    "query_end": "2025-07-02T00:00:00+00:00",
    "total": 1,
}


class CalendarTestBase(unittest.TestCase):
    """Common setup: create an offline FablibManager instance."""

    DUMMY_TOKEN_LOCATION = str(
        pathlib.Path(__file__).parent / "data" / "dummy-token.json"
    )
    FABRIC_RC_LOCATION = str(pathlib.Path(__file__).parent / "data" / "dummy_fabric_rc")

    def setUp(self):
        os.environ.clear()
        self.fablib = FablibManager(
            token_location=self.DUMMY_TOKEN_LOCATION,
            offline=True,
            project_id="DUMMY_PROJECT_ID",
            bastion_username="DUMMY_BASTION_USER",
            fabric_rc=self.FABRIC_RC_LOCATION,
        )


class TestResourcesCalendarValidation(CalendarTestBase):
    """Test input validation in resources_calendar()."""

    def _times(self, hours=2):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=hours)
        return start, end

    def test_raises_when_start_equals_end(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        with self.assertRaises(ValueError) as ctx:
            self.fablib.resources_calendar(start=start, end=start)
        self.assertIn("start must be before end", str(ctx.exception))

    def test_raises_when_start_after_end(self):
        start = datetime.datetime(2025, 7, 2, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        with self.assertRaises(ValueError) as ctx:
            self.fablib.resources_calendar(start=start, end=end)
        self.assertIn("start must be before end", str(ctx.exception))

    def test_raises_when_time_range_too_short(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(minutes=30)
        with self.assertRaises(Exception) as ctx:
            self.fablib.resources_calendar(start=start, end=end)
        self.assertIn("at least 60 minutes", str(ctx.exception))

    def test_exactly_60_minutes_does_not_raise(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(minutes=60)
        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = EMPTY_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            # Should not raise; output format doesn't matter for this test
            self.fablib.resources_calendar(
                start=start, end=end, output="list", quiet=True
            )


class TestResourcesCalendarManagerCall(CalendarTestBase):
    """Test that resources_calendar() correctly calls the manager."""

    def test_default_params_forwarded(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=4)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = EMPTY_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            self.fablib.resources_calendar(
                start=start, end=end, output="list", quiet=True
            )

        mock_manager.resources_calendar.assert_called_once_with(
            start=start,
            end=end,
            interval="day",
            site=None,
            host=None,
            exclude_site=None,
            exclude_host=None,
        )

    def test_all_params_forwarded(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            self.fablib.resources_calendar(
                start=start,
                end=end,
                interval="hour",
                site=["RENC"],
                host=["host1"],
                exclude_site=["UCSD"],
                exclude_host=["host2"],
                output="list",
                quiet=True,
            )

        mock_manager.resources_calendar.assert_called_once_with(
            start=start,
            end=end,
            interval="hour",
            site=["RENC"],
            host=["host1"],
            exclude_site=["UCSD"],
            exclude_host=["host2"],
        )

    def test_interval_week_forwarded(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(days=14)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = EMPTY_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            self.fablib.resources_calendar(
                start=start,
                end=end,
                interval="week",
                output="list",
                quiet=True,
            )

        call_kwargs = mock_manager.resources_calendar.call_args[1]
        self.assertEqual(call_kwargs["interval"], "week")

    def test_output_list_returns_rows(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.resources_calendar(
                start=start,
                end=end,
                output="list",
                quiet=True,
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        # First row is the site
        self.assertEqual(result[0]["Type"], "site")
        self.assertEqual(result[0]["Name"], "RENC")
        self.assertEqual(result[0]["Cores (avail/cap)"], "100/128")
        # Second row is the host
        self.assertEqual(result[1]["Type"], "host")
        self.assertEqual(result[1]["Name"], "renc-w1.fabric-testbed.net")
        self.assertEqual(result[1]["Cores (avail/cap)"], "32/64")
        self.assertEqual(result[1]["GPU Tesla T4"], "2/4")

    def test_filter_function_applied(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.resources_calendar(
                start=start,
                end=end,
                output="list",
                quiet=True,
                filter_function=lambda r: r["Name"] == "NONEXISTENT",
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_show_sites_only(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.resources_calendar(
                start=start,
                end=end,
                show="sites",
                output="list",
                quiet=True,
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Type"], "site")
        self.assertEqual(result[0]["Name"], "RENC")

    def test_show_hosts_only(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.resources_calendar(
                start=start,
                end=end,
                show="hosts",
                output="list",
                quiet=True,
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Type"], "host")
        self.assertEqual(result[0]["Name"], "renc-w1.fabric-testbed.net")

    def test_show_all_returns_both(self):
        start = datetime.datetime(2025, 7, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(hours=24)

        mock_manager = MagicMock()
        mock_manager.resources_calendar.return_value = SAMPLE_CALENDAR

        with patch.object(self.fablib, "get_manager", return_value=mock_manager):
            result = self.fablib.resources_calendar(
                start=start,
                end=end,
                show="all",
                output="list",
                quiet=True,
            )

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        types = [r["Type"] for r in result]
        self.assertIn("site", types)
        self.assertIn("host", types)


if __name__ == "__main__":
    unittest.main()
