# 🌩️ ApiStorm (LoadForge alternative)

A powerful, modern API Load Testing tool written in Python. Optimized for real-world scenarios, built on `asyncio` for high concurrency, and inspired by JMeter, k6, and Artillery.

## Features
- **Highly Concurrent**: Powered by `aiohttp` and `asyncio` for massive RPS.
- **Scenario Stages**: Supports ramp-up, steady load, spike, and soak tests based on stages.
- **Format Flexibility**: CSV data injection, dynamic REST JSON payloads, and dynamic headers.
- **Live Output**: Beautiful live console metrics via `rich`.
- **Rich Reporting**: Outputs structured HTML graphical reports with `Chart.js` & Raw CSVs.

## Installation

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Run an example scenario:
```bash
python main.py scenarios/example_scenario.yaml --csv output.csv --html output.html
```

## Creating Scenarios

Configure tests using easy-to-read YAML. See `scenarios/example_scenario.yaml` to learn about:
- Target VUs (Virtual Users) using `stages`
- Rest APIs (`target_url`, `method`, `headers`, `payload`)
- Ramp-up times & Think times!

## Advanced Scenarios
Create stages to define typical patterns:
- **Soak Test**: Long duration stage at an average target VUs.
- **Stress Test**: Continuously ascending targets.

Enjoy testing with ApiStorm!
