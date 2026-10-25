"""S01 daily launchd release contract; run during final verification, not development."""
from pathlib import Path
import plistlib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class S01DailyLaunchdContractTests(unittest.TestCase):
    def test_daily_schedule_is_isolated_and_enabled_only_by_install(self):
        with (ROOT / "deploy/com.stanley.signalforge-s01-news-daily.plist").open("rb") as handle:
            job = plistlib.load(handle)
        self.assertEqual(job["Label"], "com.stanley.signalforge-s01-news-daily")
        self.assertEqual(job["StartCalendarInterval"], {"Hour": 17, "Minute": 0})
        self.assertTrue(job["RunAtLoad"])
        self.assertEqual(job["StartInterval"], 3600)
        self.assertIn("Application Support/SignalForge/runtime/run-s01-news-daily.zsh", job["ProgramArguments"][-1])

    def test_wrapper_explicitly_publishes_via_bangkok(self):
        wrapper = (ROOT / "deploy/run-s01-news-daily.zsh").read_text()
        self.assertIn("signalforge.s01_daily_schedule", wrapper)
        schedule = (ROOT / "signalforge/s01_daily_schedule.py").read_text()
        self.assertIn('host="vps-bangkok"', schedule)
        self.assertIn("transfer(", schedule)
        self.assertNotIn("daily-cycle", wrapper)
