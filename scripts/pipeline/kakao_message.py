"""Builds the exact KakaoTalk summary message: ticker, price, investment
weather score, and the GitHub Pages report link."""

from scripts.pipeline.weather_score import WeatherResult


def build_kakao_message(ticker: str, company: str, price: str, weather: WeatherResult, url: str) -> str:
    return (
        f"[{company}({ticker})] 투자 분석\n"
        f"현재가: {price}\n"
        f"투자날씨: {weather.icon} {weather.score}점 ({weather.label})\n"
        f"📄 상세 리포트: {url}"
    )
