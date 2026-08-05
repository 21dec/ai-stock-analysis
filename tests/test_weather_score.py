import unittest

from scripts.pipeline.weather_score import compute_weather_score, WeatherResult


class ComputeWeatherScoreTests(unittest.TestCase):
    def test_strong_bullish_signal_yields_sunny(self):
        result = compute_weather_score(
            signal_score_10=9.0, confidence="HIGH", mtf_alignment_3=3, rsi=55.0
        )
        self.assertIsInstance(result, WeatherResult)
        # signal: 9.0*10*0.5=45, confidence: 100*0.2=20, mtf: 100*0.2=20, rsi(neutral): 100*0.1=10 -> 95
        self.assertEqual(result.score, 95)
        self.assertEqual(result.icon, "☀️")
        self.assertEqual(result.label, "맑음")

    def test_weak_bearish_signal_yields_storm(self):
        result = compute_weather_score(
            signal_score_10=1.0, confidence="LOW", mtf_alignment_3=0, rsi=75.0
        )
        # signal: 1.0*10*0.5=5, confidence: 30*0.2=6, mtf: 0*0.2=0, rsi(overbought): 50*0.1=5 -> 16
        self.assertEqual(result.score, 16)
        self.assertEqual(result.icon, "⛈️")
        self.assertEqual(result.label, "폭풍")

    def test_band_boundaries(self):
        # Each case picks confidence/mtf/rsi fixtures so signal_score_10 stays within
        # [0, 10] while the weighted total lands exactly on the boundary score. The
        # 0/폭풍 boundary is not separately tested here — it is unreachable with a
        # valid signal_score_10 (the formula's true minimum is 11, not 0) and is
        # already covered by test_weak_bearish_signal_yields_storm (score=16).
        cases = [
            # target_score, icon, label, signal_score_10, confidence, mtf_alignment_3, rsi
            (80, "☀️", "맑음", 6.0, "HIGH", 3, 50.0),
            (60, "🌤️", "대체로 맑음", 8.8, "LOW", 0, 50.0),
            (40, "⛅", "흐림", 4.8, "LOW", 0, 50.0),
            (20, "🌧️", "비", 0.8, "LOW", 0, 50.0),
        ]
        for target_score, icon, label, signal_score_10, confidence, mtf_alignment_3, rsi in cases:
            result = compute_weather_score(
                signal_score_10=signal_score_10,
                confidence=confidence,
                mtf_alignment_3=mtf_alignment_3,
                rsi=rsi,
            )
            self.assertEqual(result.score, target_score, msg=f"target={target_score}")
            self.assertEqual(result.icon, icon)
            self.assertEqual(result.label, label)

    def test_rejects_out_of_range_signal_score(self):
        with self.assertRaises(ValueError):
            compute_weather_score(signal_score_10=10.5, confidence="HIGH", mtf_alignment_3=3, rsi=50.0)

    def test_rejects_out_of_range_mtf_alignment(self):
        with self.assertRaises(ValueError):
            compute_weather_score(signal_score_10=5.0, confidence="HIGH", mtf_alignment_3=4, rsi=50.0)

    def test_rejects_unknown_confidence(self):
        with self.assertRaises(ValueError):
            compute_weather_score(signal_score_10=5.0, confidence="EXTREME", mtf_alignment_3=2, rsi=50.0)


if __name__ == "__main__":
    unittest.main()
