"""Investment weather score: a 0-100 rating derived from technical-analysis
signal outputs, independent of the skill's own 0-10 score."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherResult:
    score: int
    icon: str
    label: str


_CONFIDENCE_POINTS = {"HIGH": 100.0, "MEDIUM": 60.0, "LOW": 30.0}

_BANDS = (
    (80, "☀️", "맑음"),
    (60, "🌤️", "대체로 맑음"),
    (40, "⛅", "흐림"),
    (20, "🌧️", "비"),
    (0, "⛈️", "폭풍"),
)


def _confidence_points(confidence: str) -> float:
    key = confidence.strip().upper()
    if key not in _CONFIDENCE_POINTS:
        raise ValueError(f"unknown confidence level: {confidence!r}")
    return _CONFIDENCE_POINTS[key]


def _rsi_points(rsi: float) -> float:
    if rsi > 70 or rsi < 30:
        return 50.0
    if 40 <= rsi <= 60:
        return 100.0
    return 70.0


def _weather_label(score: int):
    for threshold, icon, label in _BANDS:
        if score >= threshold:
            return icon, label
    # unreachable: _BANDS covers down to 0 and score is clamped to >= 0
    return _BANDS[-1][1], _BANDS[-1][2]


def compute_weather_score(
    signal_score_10: float, confidence: str, mtf_alignment_3: int, rsi: float
) -> WeatherResult:
    if not (0.0 <= signal_score_10 <= 10.0):
        raise ValueError(f"signal_score_10 must be within 0..10, got {signal_score_10}")
    if not (0 <= mtf_alignment_3 <= 3):
        raise ValueError(f"mtf_alignment_3 must be within 0..3, got {mtf_alignment_3}")

    signal_points = signal_score_10 * 10.0
    confidence_points = _confidence_points(confidence)
    mtf_points = (mtf_alignment_3 / 3.0) * 100.0
    rsi_points = _rsi_points(rsi)

    total = (
        signal_points * 0.5
        + confidence_points * 0.2
        + mtf_points * 0.2
        + rsi_points * 0.1
    )
    score = max(0, min(100, round(total)))
    icon, label = _weather_label(score)
    return WeatherResult(score=score, icon=icon, label=label)
