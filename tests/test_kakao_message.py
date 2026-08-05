import unittest

from scripts.pipeline.kakao_message import build_kakao_message
from scripts.pipeline.weather_score import WeatherResult


class BuildKakaoMessageTests(unittest.TestCase):
    def test_exact_message_format(self):
        weather = WeatherResult(score=82, icon="☀️", label="맑음")
        message = build_kakao_message(
            ticker="AAPL",
            company="Apple Inc.",
            price="$185.32",
            weather=weather,
            url="https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html",
        )
        expected = (
            "[Apple Inc.(AAPL)] 투자 분석\n"
            "현재가: $185.32\n"
            "투자날씨: ☀️ 82점 (맑음)\n"
            "📄 상세 리포트: https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html"
        )
        self.assertEqual(message, expected)


if __name__ == "__main__":
    unittest.main()
