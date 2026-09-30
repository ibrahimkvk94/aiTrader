import io
import json
import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from priceaction.feed import download_bist_daily, download


def payload(gap=None):
    start = datetime(2026, 1, 1, 7, tzinfo=timezone.utc)
    stamps = [int((start+timedelta(days=i)).timestamp()) for i in range(220)]
    quote = {key: [value]*220 for key, value in (("open",100),("high",102),("low",98),("close",101),("volume",1000))}
    if gap is not None:
        for key in quote:
            quote[key][gap] = None
    return {"chart": {"error": None, "result": [{"meta": {"exchangeName":"IST"},
            "timestamp": stamps, "indicators": {"quote": [quote]}}]}}


class FeedTests(unittest.TestCase):
    def test_bist_unknown_gap_resets_history(self):
        fake = io.BytesIO(json.dumps(payload(gap=20)).encode())
        with patch("priceaction.feed.urlopen", return_value=fake), patch("priceaction.feed.time.time", return_value=1790766000):
            bars, meta = download_bist_daily("THYAO.IS")
        self.assertEqual(len(bars), 199)
        self.assertEqual(meta["history_reset_after_missing"], "2026-01-21")

    def test_bist_current_daily_candle_excluded(self):
        data = payload()
        now = data["chart"]["result"][0]["timestamp"][-1] + 100
        with patch("priceaction.feed.urlopen", return_value=io.BytesIO(json.dumps(data).encode())), patch("priceaction.feed.time.time", return_value=now):
            bars, _ = download_bist_daily("THYAO.IS")
        self.assertEqual(len(bars), 219)
        self.assertTrue(all(b.end <= now for b in bars))

    def test_bist_verified_holiday_is_not_an_unknown_gap(self):
        # January 1 to April 23 is 112 days in 2026.
        fake = io.BytesIO(json.dumps(payload(gap=112)).encode())
        with patch("priceaction.feed.urlopen", return_value=fake), patch("priceaction.feed.time.time", return_value=1790766000):
            bars, meta = download_bist_daily("THYAO.IS")
        self.assertEqual(len(bars), 219)
        self.assertIsNone(meta["history_reset_after_missing"])
        self.assertIn("2026-04-23", meta["verified_closed_dates"])

    def test_crypto_current_candle_excluded(self):
        with patch("priceaction.feed.public_get", side_effect=[{"serverTime": 1350000},
                   [[0,100,102,98,101,10,899999],[900000,101,102,99,100,10,1799999]]]):
            bars = download("BTCUSDT", 0)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].end, 900)


if __name__ == "__main__":
    unittest.main()
