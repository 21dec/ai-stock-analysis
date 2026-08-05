# Stock Analysis → HTML → GitHub Pages → KakaoTalk Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic, testable pieces of the stock-analysis pipeline — investment weather scoring, fixed HTML template rendering, and KakaoTalk message formatting — plus the operational documentation that tells a future Claude session how to drive them end-to-end.

**Architecture:** Small pure-function Python modules under `scripts/pipeline/` (weather score, report rendering, message building), a fixed flat/minimal HTML template under `templates/`, and a thin CLI (`scripts/generate_report.py`) that ties them together and prints the file path + KakaoTalk message for the calling agent to act on (git push, MCP send). Git push and the actual KakaoTalk send are NOT scripted — they stay as explicit agent actions per the design's error-handling rules.

**Tech Stack:** Python 3 standard library only (`unittest`, `pathlib`, `string.Template`, `json`, `argparse`, `dataclasses`). No third-party dependencies (pytest is not installed in this environment).

## Global Constraints

- No left-border accent styling anywhere in the HTML template (`border-left` / left-only accent bars are forbidden per user's global CLAUDE.md design rule) — use uniform 1px borders or background color instead.
- HTML template is flat/minimal: no gradients, no box-shadows, one accent color only.
- Weather score formula (fixed, do not change without updating the spec):
  `total = signal_score_10*10*0.5 + confidence_points*0.2 + mtf_points*0.2 + rsi_points*0.1`, clamped to `[0, 100]` and rounded to an int.
  - `confidence_points`: HIGH=100, MEDIUM=60, LOW=30.
  - `mtf_points = (mtf_alignment_3 / 3) * 100`.
  - `rsi_points`: 50 if RSI>70 or RSI<30; 100 if 40<=RSI<=60; else 70.
- Weather icon/label bands (score → icon, short label): 80–100 ☀️ 맑음; 60–79 🌤️ 대체로 맑음; 40–59 ⛅ 흐림; 20–39 🌧️ 비; 0–19 ⛈️ 폭풍.
- Report file path: `docs/reports/<TICKER>-<YYYYMMDD>.html` (TICKER uppercased).
- GitHub Pages URL pattern: `https://<owner>.github.io/<repo>/reports/<TICKER>-<YYYYMMDD>.html`, default repo `21dec/ai-stock-analysis`.
- KakaoTalk message format (exact structure):
  ```
  [<company>(<ticker>)] 투자 분석
  현재가: <price>
  투자날씨: <icon> <score>점 (<label>)
  📄 상세 리포트: <url>
  ```
- Git push failures must never be force-retried automatically; report the failure instead.
- If the KakaoTalk send tool is unavailable, the HTML/push steps still complete and the failure is reported explicitly — never silently skipped or substituted with another channel.

---

## File Structure

```
templates/report-template.html          # fixed flat/minimal HTML template (string.Template placeholders)
scripts/pipeline/__init__.py             # empty, makes pipeline a package
scripts/pipeline/weather_score.py        # compute_weather_score() pure function
scripts/pipeline/report_builder.py       # render_report(), report_filename(), report_path(), pages_url()
scripts/pipeline/kakao_message.py        # build_kakao_message()
scripts/generate_report.py               # CLI: reads JSON, writes HTML file, prints path/url/message as JSON
tests/test_weather_score.py
tests/test_report_builder.py
tests/test_kakao_message.py
tests/test_generate_report.py
KAKAOTALK_DELIVERY_POLICY.md             # rewritten to reflect summary+link format
PIPELINE.md                              # operational runbook for future Claude sessions
```

---

### Task 1: Investment weather score calculator

**Files:**
- Create: `scripts/pipeline/__init__.py`
- Create: `scripts/pipeline/weather_score.py`
- Test: `tests/test_weather_score.py`

**Interfaces:**
- Consumes: nothing (pure function, no dependencies on other tasks).
- Produces: `WeatherResult` dataclass with fields `score: int`, `icon: str`, `label: str`. Function `compute_weather_score(signal_score_10: float, confidence: str, mtf_alignment_3: int, rsi: float) -> WeatherResult`. Later tasks (2, 3, 4) import `from scripts.pipeline.weather_score import compute_weather_score, WeatherResult`.

- [ ] **Step 1: Create the package init file**

```bash
mkdir -p scripts/pipeline tests
touch scripts/pipeline/__init__.py
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_weather_score.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest tests.test_weather_score -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'scripts.pipeline.weather_score'` (module doesn't exist yet).

- [ ] **Step 4: Write the implementation**

Create `scripts/pipeline/weather_score.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_weather_score -v`
Expected: `OK` — all 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/pipeline/__init__.py scripts/pipeline/weather_score.py tests/test_weather_score.py
git commit -m "Add investment weather score calculator"
```

---

### Task 2: Fixed HTML template and report builder

**Files:**
- Create: `templates/report-template.html`
- Create: `scripts/pipeline/report_builder.py`
- Test: `tests/test_report_builder.py`

**Interfaces:**
- Consumes: nothing directly (does not import Task 1's module — the CLI in Task 4 wires the two together).
- Produces:
  - `render_report(context: dict, template_path: Path | None = None) -> str`
  - `report_filename(ticker: str, report_date: str) -> str`
  - `report_path(ticker: str, report_date: str, docs_dir: Path) -> Path`
  - `pages_url(ticker: str, report_date: str, repo: str = "21dec/ai-stock-analysis") -> str`
  - Constant `REQUIRED_CONTEXT_KEYS: frozenset[str]` listing every placeholder the template requires.
  Task 4 imports all four functions and the constant from `scripts.pipeline.report_builder`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_report_builder.py`:

```python
import tempfile
import unittest
from pathlib import Path

from scripts.pipeline.report_builder import (
    REQUIRED_CONTEXT_KEYS,
    pages_url,
    render_report,
    report_filename,
    report_path,
)

SAMPLE_CONTEXT = {
    "TICKER": "AAPL",
    "COMPANY": "Apple Inc.",
    "DATE": "2026-08-05",
    "PRICE": "$185.32",
    "WEATHER_ICON": "☀️",
    "WEATHER_SCORE": "82",
    "WEATHER_LABEL": "맑음",
    "SIGNAL": "BULLISH",
    "SIGNAL_CLASS": "bullish",
    "CONFIDENCE": "HIGH",
    "HORIZON": "LONG-TERM",
    "ANALYSIS_BODY_HTML": "<h2>Summary</h2><p>Test body.</p>",
}


class RenderReportTests(unittest.TestCase):
    def test_renders_all_placeholders(self):
        html = render_report(SAMPLE_CONTEXT)
        self.assertIn("AAPL", html)
        self.assertIn("Apple Inc.", html)
        self.assertIn("$185.32", html)
        self.assertIn("82", html)
        self.assertIn('class="badge signal-badge bullish"', html)
        self.assertIn("<h2>Summary</h2><p>Test body.</p>", html)
        # design constraint: no left-border accent styling anywhere
        self.assertNotIn("border-left", html)

    def test_missing_key_raises(self):
        incomplete = dict(SAMPLE_CONTEXT)
        del incomplete["TICKER"]
        with self.assertRaises(ValueError):
            render_report(incomplete)

    def test_required_keys_matches_sample_context(self):
        self.assertEqual(REQUIRED_CONTEXT_KEYS, frozenset(SAMPLE_CONTEXT.keys()))


class PathHelperTests(unittest.TestCase):
    def test_report_filename(self):
        self.assertEqual(report_filename("aapl", "20260805"), "AAPL-20260805.html")

    def test_report_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            result = report_path("aapl", "20260805", docs_dir)
            self.assertEqual(result, docs_dir / "reports" / "AAPL-20260805.html")

    def test_pages_url_default_repo(self):
        url = pages_url("aapl", "20260805")
        self.assertEqual(
            url, "https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html"
        )

    def test_pages_url_custom_repo(self):
        url = pages_url("tsla", "20260101", repo="someone/other-repo")
        self.assertEqual(
            url, "https://someone.github.io/other-repo/reports/TSLA-20260101.html"
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest tests.test_report_builder -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'scripts.pipeline.report_builder'`.

- [ ] **Step 3: Create the fixed HTML template**

Create `templates/report-template.html`:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${TICKER} 투자 분석 리포트 - ${DATE}</title>
<style>
  :root {
    --accent: #2563eb;
    --text: #1f2937;
    --text-muted: #6b7280;
    --border: #e5e7eb;
    --bg: #ffffff;
    --bg-subtle: #f9fafb;
    --bullish: #059669;
    --bearish: #dc2626;
    --neutral: #6b7280;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: var(--text);
    background: var(--bg);
    line-height: 1.6;
    max-width: 760px;
    margin: 0 auto;
    padding: 32px 20px 64px;
  }
  .titlebar {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    margin-bottom: 20px;
  }
  .titlebar .name { font-size: 20px; font-weight: 700; }
  .titlebar .date { font-size: 13px; color: var(--text-muted); }
  .price { font-size: 32px; font-weight: 700; margin-bottom: 16px; }
  .badge-row { display: flex; gap: 10px; margin-bottom: 28px; flex-wrap: wrap; }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--border);
    background: var(--bg-subtle);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 600;
  }
  .signal-badge.bullish { color: var(--bullish); border-color: var(--bullish); }
  .signal-badge.bearish { color: var(--bearish); border-color: var(--bearish); }
  .signal-badge.neutral { color: var(--neutral); border-color: var(--neutral); }
  .analysis-body h2 {
    font-size: 16px;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }
  .analysis-body table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
  .analysis-body th, .analysis-body td { border: 1px solid var(--border); padding: 8px 10px; text-align: left; }
  .analysis-body th { background: var(--bg-subtle); font-weight: 600; }
  .analysis-body ul, .analysis-body ol { margin: 8px 0 8px 20px; }
  .footer {
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--text-muted);
  }
</style>
</head>
<body>
  <div class="titlebar">
    <span class="name">${COMPANY} (${TICKER})</span>
    <span class="date">${DATE}</span>
  </div>
  <div class="price">${PRICE}</div>
  <div class="badge-row">
    <span class="badge weather-badge">${WEATHER_ICON} ${WEATHER_SCORE}점 &middot; ${WEATHER_LABEL}</span>
    <span class="badge signal-badge ${SIGNAL_CLASS}">${SIGNAL} &middot; ${CONFIDENCE} &middot; ${HORIZON}</span>
  </div>
  <div class="analysis-body">
${ANALYSIS_BODY_HTML}
  </div>
  <div class="footer">
    본 리포트는 AI가 생성한 정보 제공용 자료이며 투자 자문이 아닙니다. 투자 결정 전에 반드시 별도로 검증하시기 바랍니다.
  </div>
</body>
</html>
```

- [ ] **Step 4: Write the implementation**

Create `scripts/pipeline/report_builder.py`:

```python
"""Renders the fixed flat/minimal HTML report template and computes the
deterministic file path / GitHub Pages URL for a given ticker + date."""

from pathlib import Path
from string import Template

_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "report-template.html"

REQUIRED_CONTEXT_KEYS = frozenset(
    {
        "TICKER",
        "COMPANY",
        "DATE",
        "PRICE",
        "WEATHER_ICON",
        "WEATHER_SCORE",
        "WEATHER_LABEL",
        "SIGNAL",
        "SIGNAL_CLASS",
        "CONFIDENCE",
        "HORIZON",
        "ANALYSIS_BODY_HTML",
    }
)


def render_report(context: dict, template_path: Path = _TEMPLATE_PATH) -> str:
    missing = REQUIRED_CONTEXT_KEYS - context.keys()
    if missing:
        raise ValueError(f"missing template context keys: {sorted(missing)}")
    template_text = template_path.read_text(encoding="utf-8")
    return Template(template_text).substitute(context)


def report_filename(ticker: str, report_date: str) -> str:
    return f"{ticker.upper()}-{report_date}.html"


def report_path(ticker: str, report_date: str, docs_dir: Path) -> Path:
    return docs_dir / "reports" / report_filename(ticker, report_date)


def pages_url(ticker: str, report_date: str, repo: str = "21dec/ai-stock-analysis") -> str:
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/reports/{report_filename(ticker, report_date)}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_report_builder -v`
Expected: `OK` — all 7 tests pass.

- [ ] **Step 6: Commit**

```bash
git add templates/report-template.html scripts/pipeline/report_builder.py tests/test_report_builder.py
git commit -m "Add fixed flat/minimal HTML report template and builder"
```

---

### Task 3: KakaoTalk message builder

**Files:**
- Create: `scripts/pipeline/kakao_message.py`
- Test: `tests/test_kakao_message.py`

**Interfaces:**
- Consumes: `WeatherResult` from Task 1 (`scripts.pipeline.weather_score.WeatherResult`) — imported by type only, not instantiated internally.
- Produces: `build_kakao_message(ticker: str, company: str, price: str, weather: WeatherResult, url: str) -> str`. Task 4 imports this function from `scripts.pipeline.kakao_message`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_kakao_message.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m unittest tests.test_kakao_message -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'scripts.pipeline.kakao_message'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/pipeline/kakao_message.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m unittest tests.test_kakao_message -v`
Expected: `OK` — 1 test passes.

- [ ] **Step 5: Commit**

```bash
git add scripts/pipeline/kakao_message.py tests/test_kakao_message.py
git commit -m "Add KakaoTalk summary message builder"
```

---

### Task 4: CLI entrypoint tying the pipeline together

**Files:**
- Create: `scripts/generate_report.py`
- Test: `tests/test_generate_report.py`

**Interfaces:**
- Consumes:
  - `compute_weather_score`, `WeatherResult` from Task 1
  - `render_report`, `report_path`, `pages_url` from Task 2
  - `build_kakao_message` from Task 3
- Produces: a `main(argv: list[str]) -> int` function and a `build_context(data: dict, weather: WeatherResult) -> dict` helper, both importable from `scripts.generate_report`. Running the module as a script (`python3 scripts/generate_report.py <input.json> [--docs-dir PATH] [--repo OWNER/NAME]`) writes the HTML file and prints a single JSON object to stdout: `{"report_path": "...", "pages_url": "...", "kakao_message": "..."}`. This is the contract the operational runbook (Task 5) documents for the calling agent.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_generate_report.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_report import build_context, main


SAMPLE_INPUT = {
    "ticker": "AAPL",
    "company": "Apple Inc.",
    "date": "20260805",
    "price": "$185.32",
    "signal_score_10": 8.4,
    "confidence": "HIGH",
    "mtf_alignment_3": 3,
    "rsi": 55.0,
    "signal": "BULLISH",
    "horizon": "LONG-TERM",
    "analysis_body_html": "<h2>Summary</h2><p>Test body.</p>",
}


class BuildContextTests(unittest.TestCase):
    def test_signal_class_lowercased(self):
        from scripts.pipeline.weather_score import compute_weather_score

        weather = compute_weather_score(
            signal_score_10=SAMPLE_INPUT["signal_score_10"],
            confidence=SAMPLE_INPUT["confidence"],
            mtf_alignment_3=SAMPLE_INPUT["mtf_alignment_3"],
            rsi=SAMPLE_INPUT["rsi"],
        )
        context = build_context(SAMPLE_INPUT, weather)
        self.assertEqual(context["SIGNAL_CLASS"], "bullish")
        self.assertEqual(context["TICKER"], "AAPL")
        self.assertEqual(context["ANALYSIS_BODY_HTML"], "<h2>Summary</h2><p>Test body.</p>")


class MainCliTests(unittest.TestCase):
    def test_writes_html_and_prints_json_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "input.json"
            input_path.write_text(json.dumps(SAMPLE_INPUT), encoding="utf-8")
            docs_dir = tmp_path / "docs"

            import io
            import contextlib

            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                exit_code = main([str(input_path), "--docs-dir", str(docs_dir)])

            self.assertEqual(exit_code, 0)
            result = json.loads(captured.getvalue())

            expected_report_path = docs_dir / "reports" / "AAPL-20260805.html"
            self.assertEqual(Path(result["report_path"]), expected_report_path)
            self.assertTrue(expected_report_path.exists())

            html = expected_report_path.read_text(encoding="utf-8")
            self.assertIn("AAPL", html)
            self.assertIn("<h2>Summary</h2><p>Test body.</p>", html)

            self.assertEqual(
                result["pages_url"],
                "https://21dec.github.io/ai-stock-analysis/reports/AAPL-20260805.html",
            )
            self.assertIn("AAPL", result["kakao_message"])
            self.assertIn(result["pages_url"], result["kakao_message"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m unittest tests.test_generate_report -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'scripts.generate_report'`.

- [ ] **Step 3: Write the implementation**

Create `scripts/generate_report.py`:

```python
"""CLI entrypoint: reads a JSON analysis payload, computes the investment
weather score, renders the fixed HTML report, writes it to disk, and prints
the report path / GitHub Pages URL / KakaoTalk message as JSON.

This script does NOT git add/commit/push and does NOT send the KakaoTalk
message itself — those remain explicit agent actions (see PIPELINE.md).
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.pipeline.kakao_message import build_kakao_message
from scripts.pipeline.report_builder import pages_url, render_report, report_path
from scripts.pipeline.weather_score import WeatherResult, compute_weather_score

REPO_ROOT = Path(__file__).resolve().parents[1]


def build_context(data: dict, weather: WeatherResult) -> dict:
    return {
        "TICKER": data["ticker"].upper(),
        "COMPANY": data["company"],
        "DATE": data["date"],
        "PRICE": data["price"],
        "WEATHER_ICON": weather.icon,
        "WEATHER_SCORE": str(weather.score),
        "WEATHER_LABEL": weather.label,
        "SIGNAL": data["signal"],
        "SIGNAL_CLASS": data["signal"].lower(),
        "CONFIDENCE": data["confidence"],
        "HORIZON": data["horizon"],
        "ANALYSIS_BODY_HTML": data["analysis_body_html"],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate a stock analysis HTML report.")
    parser.add_argument("input_json", help="Path to a JSON file describing the analysis.")
    parser.add_argument(
        "--docs-dir",
        default=str(REPO_ROOT / "docs"),
        help="Docs directory that is the GitHub Pages source (default: <repo>/docs).",
    )
    parser.add_argument(
        "--repo",
        default="21dec/ai-stock-analysis",
        help="GitHub owner/repo used to build the Pages URL.",
    )
    args = parser.parse_args(argv)

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    weather = compute_weather_score(
        signal_score_10=data["signal_score_10"],
        confidence=data["confidence"],
        mtf_alignment_3=data["mtf_alignment_3"],
        rsi=data["rsi"],
    )

    context = build_context(data, weather)
    html = render_report(context)

    docs_dir = Path(args.docs_dir)
    output_path = report_path(data["ticker"], data["date"], docs_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    url = pages_url(data["ticker"], data["date"], repo=args.repo)
    message = build_kakao_message(
        ticker=data["ticker"].upper(),
        company=data["company"],
        price=data["price"],
        weather=weather,
        url=url,
    )

    result = {
        "report_path": str(output_path),
        "pages_url": url,
        "kakao_message": message,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. python3 -m unittest tests.test_generate_report -v`
Expected: `OK` — 2 tests pass.

- [ ] **Step 5: Run the full test suite to confirm nothing else broke**

Run: `PYTHONPATH=. python3 -m unittest discover -s tests -v`
Expected: `OK` — all tests across all four test files pass (weather score: 6, report builder: 7, kakao message: 1, generate report: 2 = 16 total).

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_report.py tests/test_generate_report.py
git commit -m "Add CLI entrypoint wiring weather score, report render, and KakaoTalk message"
```

---

### Task 5: Update the KakaoTalk delivery policy document

**Files:**
- Modify: `KAKAOTALK_DELIVERY_POLICY.md` (full rewrite)

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: nothing importable — this is the policy doc that Task 6's runbook references.

- [ ] **Step 1: Replace the policy document**

Read the current file first, then overwrite `KAKAOTALK_DELIVERY_POLICY.md` with:

```markdown
# 카카오톡 주식 분석 전송 정책

## 배경

이전 정책은 분석 전문을 그대로 한 메시지로 전송하는 방식이었다. 이제는 분석 결과를
`docs/reports/<TICKER>-<YYYYMMDD>.html`로 생성해 GitHub Pages에 게시하고, 카카오톡에는
요약 + 링크만 전송하는 방식으로 바뀌었다. 상세 근거(지지·저항, 볼린저 밴드·RSI, 확인·무효화
조건 등)는 링크를 열어 확인하는 구조다.

## 메시지 포맷 (고정)

```
[<회사명>(<티커>)] 투자 분석
현재가: <가격>
투자날씨: <아이콘> <점수>점 (<라벨>)
📄 상세 리포트: <GitHub Pages 링크>
```

- 이 4줄 형식을 벗어나지 않는다. 분석 전문을 메시지에 다시 붙여넣지 않는다.
- 투자날씨 점수와 아이콘/라벨은 `scripts/pipeline/weather_score.py`의
  `compute_weather_score()` 산정 결과를 그대로 사용한다.

## 전송 원칙

- HTML 리포트 생성 및 git push가 완료된 뒤에만 카카오톡 메시지를 전송한다.
- 카카오톡 발송 도구(PlayMCP `KakaotalkChat_MemoChat` 등)가 연결되어 있지 않으면,
  HTML 생성/push는 완료된 상태로 두고 발송 실패와 원인을 사용자에게 명확히 보고한다.
  자동으로 다른 채널로 대체하거나 조용히 생략하지 않는다.
- 한 메시지의 성공 응답을 받은 뒤에만 해당 요청을 완료 처리한다.
- 실제 전송 오류가 발생하면 자동으로 형식을 바꾸거나 재시도하지 않고 실패 원인을 보고한다.
```

- [ ] **Step 2: Commit**

```bash
git add KAKAOTALK_DELIVERY_POLICY.md
git commit -m "Update KakaoTalk delivery policy for summary+link report format"
```

---

### Task 6: Operational runbook for future Claude sessions

**Files:**
- Create: `PIPELINE.md`

**Interfaces:**
- Consumes: the JSON schema produced by Task 4's `build_context`/`main` (documents the exact keys `generate_report.py` expects).
- Produces: nothing importable — this is the doc a future Claude session reads before running the pipeline.

- [ ] **Step 1: Write the runbook**

Create `PIPELINE.md`:

```markdown
# 주식 분석 파이프라인 실행 방법 (Claude용 운영 가이드)

사용자가 "OOO 분석해서 보내줘" 라고 요청하면 아래 순서를 그대로 따른다.
설계 배경은 `superpowers/specs/2026-08-05-stock-analysis-pipeline-design.md` 참고.

## 사전 조건 (1회성 — 아직 완료되지 않았다면 사용자에게 안내)

1. **GitHub Pages**: `21dec/ai-stock-analysis` 저장소가 public이고, `main` 브랜치의
   `/docs` 폴더가 Pages 소스로 설정되어 있어야 한다. 안 되어 있으면 사용자에게
   GitHub 웹 UI(Settings → Pages → Source: `main` / `docs`)에서 설정을 요청한다.
2. **카카오톡 발송 도구**: PlayMCP `KakaotalkChat_MemoChat` (또는 동등한) MCP 도구가
   세션에 연결되어 있어야 한다. 연결되어 있지 않으면 4~5단계(HTML 생성, git push)는
   진행하고, 6단계(카카오톡 발송)에서 도구 미연결을 사용자에게 명확히 보고한다.

## 실행 순서

1. **종목 식별** — 회사명이 주어지면 티커 심볼로 매핑한다 (예: "애플" → `AAPL`).
2. **분석 실행** — `us-stock-analysis:technical-analysis` 스킬을 실행해 최신 시세와
   표준 출력(MA, RSI, MACD, 볼린저, MTF 정렬 점수, 시그널 박스, Thesis Invalidation)을
   얻는다. 스킬의 데이터 검증 규칙(라이브 데이터 없으면 경고 표시)을 그대로 따른다.
3. **입력 JSON 작성** — 스킬 출력에서 다음 값을 추출해 임시 JSON 파일로 만든다
   (예: `/tmp/report-input.json`):

   ```json
   {
     "ticker": "AAPL",
     "company": "Apple Inc.",
     "date": "20260805",
     "price": "$185.32",
     "signal_score_10": 8.4,
     "confidence": "HIGH",
     "mtf_alignment_3": 3,
     "rsi": 55.0,
     "signal": "BULLISH",
     "horizon": "LONG-TERM",
     "analysis_body_html": "<h2>추세</h2><p>...</p><h2>지지/저항</h2><table>...</table>..."
   }
   ```

   - `signal_score_10`: 스킬이 출력하는 `Score: X.X / 10` 값.
   - `confidence`: 스킬이 출력하는 `Confidence: HIGH/MEDIUM/LOW`.
   - `mtf_alignment_3`: MTF 정렬 점수 `X/3`의 `X`.
   - `rsi`: 가장 최근(주로 primary timeframe) RSI(14) 값.
   - `signal`: `BULLISH`/`NEUTRAL`/`BEARISH`.
   - `analysis_body_html`: 스킬이 만든 분석 본문(추세, 지지/저항, 지표, 패턴, Thesis
     Invalidation 등)을 `<h2>`/`<table>`/`<ul>` 등 기본 HTML 태그로 직접 작성한다.
     별도 변환 스크립트는 없다 — Claude가 이 HTML을 직접 작성한다.

4. **HTML 생성** — 다음 명령으로 리포트를 만든다:

   ```bash
   PYTHONPATH=. python3 scripts/generate_report.py /tmp/report-input.json
   ```

   표준출력으로 `{"report_path": "...", "pages_url": "...", "kakao_message": "..."}`
   JSON이 출력된다. 이 세 값을 이후 단계에서 사용한다.

5. **git push** — 생성된 `report_path` 파일을 커밋하고 push한다:

   ```bash
   git add docs/reports/<TICKER>-<YYYYMMDD>.html
   git commit -m "Add <TICKER> analysis report for <YYYYMMDD>"
   git push origin main
   ```

   push가 실패하면(충돌 등) 강제 push하지 않고 원인을 사용자에게 보고한다.

6. **카카오톡 발송** — 4단계에서 얻은 `kakao_message`를 PlayMCP
   `KakaotalkChat_MemoChat` 도구로 그대로 전송한다. 메시지를 축약·분할하지 않는다.
   도구가 연결되어 있지 않으면 발송 실패를 명확히 보고하고, HTML 생성/push는
   완료된 상태임을 알린다.

## 참고

- 투자날씨 점수 공식은 `scripts/pipeline/weather_score.py`에 고정되어 있다.
  공식을 바꾸려면 스펙 문서와 이 스크립트를 함께 갱신한다.
- HTML 템플릿은 `templates/report-template.html`에 고정되어 있다. 매 실행마다
  값만 채워 넣고, 템플릿 구조 자체는 바꾸지 않는다.
```

- [ ] **Step 2: Commit**

```bash
git add PIPELINE.md
git commit -m "Add operational runbook for the stock analysis pipeline"
```

---

## Final Verification

- [ ] **Step 1: Run the entire test suite one more time**

Run: `PYTHONPATH=. python3 -m unittest discover -s tests -v`
Expected: `OK` — 16 tests pass, 0 failures.

- [ ] **Step 2: Manually exercise the CLI end-to-end**

```bash
mkdir -p /tmp/pipeline-smoke-test
cat > /tmp/pipeline-smoke-test/input.json <<'JSON'
{
  "ticker": "AAPL",
  "company": "Apple Inc.",
  "date": "20260805",
  "price": "$185.32",
  "signal_score_10": 8.4,
  "confidence": "HIGH",
  "mtf_alignment_3": 3,
  "rsi": 55.0,
  "signal": "BULLISH",
  "horizon": "LONG-TERM",
  "analysis_body_html": "<h2>Summary</h2><p>Smoke test body.</p>"
}
JSON
PYTHONPATH=. python3 scripts/generate_report.py /tmp/pipeline-smoke-test/input.json \
  --docs-dir /tmp/pipeline-smoke-test/docs
cat /tmp/pipeline-smoke-test/docs/reports/AAPL-20260805.html
```

Expected: the printed JSON result line, followed by a valid, flat-styled HTML
document containing "AAPL", "Apple Inc.", "$185.32", the weather badge, the
signal badge, and "Smoke test body.". No `border-left` anywhere in the output.

- [ ] **Step 3: Clean up the smoke test directory**

```bash
rm -rf /tmp/pipeline-smoke-test
```
