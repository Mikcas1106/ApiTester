# 🌩️ ApiStorm (LoadForge alternative)

A powerful, modern API Load Testing tool written in Python. Optimized for real-world scenarios, built on `asyncio` for high concurrency, and inspired by JMeter, k6, and Artillery.

## Features
- **Highly Concurrent**: Powered by `aiohttp` and `asyncio` for massive RPS.
- **Scenario Stages**: Supports ramp-up, steady load, spike, and soak tests based on stages.
- **Format Flexibility**: CSV data injection, dynamic REST JSON payloads, and dynamic headers.
- **Live Output**: Beautiful live console metrics via `rich`.
- **Rich Reporting**: Outputs structured HTML graphical reports with `Chart.js` & Raw CSVs.

## System Setup & Installation

### 1. Prerequisites
- **Python 3.9 or higher** installed on your system.

### 2. Environment Setup (Recommended)
It is highly recommended to use a virtual environment to keep ApiStorm's dependencies isolated.
```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows):
venv\Scripts\activate
# Activate it (Mac/Linux):
source venv/bin/activate
```

### 3. Install Dependencies
Install all the required background engines (`aiohttp`, `fastapi`, `psutil`, etc.):
```bash
pip install -r requirements.txt
```

### 4. Running the ApiStorm Studio (Web UI)
ApiStorm comes with a beautiful, real-time Glassmorphism web interface where you can dynamically build stages, monitor live WebSocket charts, and analyze host system RAM/CPU metrics.
```bash
python ui.py
```
> 👉 **Open your browser and navigate to:** `http://127.0.0.1:8000`

### 5. Running the CLI (Headless Mode)
You can optionally run tests via the Terminal—perfect for integrations into CI/CD pipelines.
```bash
python main.py scenarios/example_scenario.yaml --csv output.csv --html output.html
```

## Creating YAML Scenarios

Configure tests using easy-to-read YAML. See `scenarios/example_scenario.yaml` to learn about:
- Target VUs (Virtual Users) using `stages`
- Rest APIs (`target_url`, `method`, `headers`, `payload`)
- Ramp-up times & Think times!

## Advanced Scenarios
Create stages to define typical patterns:
- **Soak Test**: Long duration stage at an average target VUs.
- **Stress Test**: Continuously ascending targets.

Enjoy testing with ApiStorm!
