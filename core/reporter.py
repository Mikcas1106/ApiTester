import asyncio
import math
import csv
import json
from collections import deque
from rich.live import Live
from rich.table import Table

class LiveReporter:
    def __init__(self, config):
        self.config = config
        self.results = []
        self.latencies = []
        self.total_reqs = 0
        self.total_errors = 0
        self.error_details = {}
        self.time_buckets = {}  # for charting RPS over time
        self.recent_reqs = deque(maxlen=10000)

    async def start(self, queue, stop_event):
        try:
            from rich.console import Console
            console = Console()
            with Live(self.generate_table(0), refresh_per_second=2, console=console) as live:
                while not stop_event.is_set() or not queue.empty():
                    try:
                        # process items fast
                        res = await asyncio.wait_for(queue.get(), timeout=0.5)
                        self._process_result(res)
                        queue.task_done()
                    except asyncio.TimeoutError:
                        pass
                    
                    self._prune_recent()
                    live.update(self.generate_table(len(self.recent_reqs)))
        except Exception as e:
            print(f"Reporter error: {e}")

    def _process_result(self, res):
        self.results.append(res)
        self.latencies.append(res["latency"])
        self.total_reqs += 1
        self.recent_reqs.append(res["timestamp"])
        
        if res["error"] or res["status"] >= 400:
            self.total_errors += 1
            msg = str(res["error"]) if res["error"] else f"HTTP {res['status']}"
            self.error_details[msg] = self.error_details.get(msg, 0) + 1
            
        sec = int(math.floor(res["timestamp"]))
        if sec not in self.time_buckets:
            self.time_buckets[sec] = {"reqs": 0, "errors": 0}
        self.time_buckets[sec]["reqs"] += 1
        if res["error"] or res["status"] >= 400:
             self.time_buckets[sec]["errors"] += 1

    def _prune_recent(self):
        import time
        curr_ts = time.time()
        while self.recent_reqs and curr_ts - self.recent_reqs[0] > 1.0:
            self.recent_reqs.popleft()

    def generate_table(self, live_rps):
        table = Table(title="🌩️ ApiStorm Live Metrics", style="bold blue")
        table.add_column("Requests", style="cyan", justify="right")
        table.add_column("Errors", style="red", justify="right")
        table.add_column("Live RPS", style="green", justify="right")
        table.add_column("Avg Latency", style="yellow", justify="right")
        
        avg_lat = sum(self.latencies) / len(self.latencies) if self.latencies else 0.0
        
        table.add_row(
            str(self.total_reqs),
            str(self.total_errors),
            str(live_rps),
            f"{avg_lat*1000:.2f} ms"
        )
        return table

    def get_final_result(self):
        if not self.latencies:
            return {"error": "No requests processed"}
        
        self.latencies.sort()
        start_ts = self.results[0]["timestamp"]
        end_ts = self.results[-1]["timestamp"]
        total_time = end_ts - start_ts
        if total_time <= 0: total_time = 1.0
        
        return {
            "total_requests": self.total_reqs,
            "total_errors": self.total_errors,
            "error_details": self.error_details,
            "rps": self.total_reqs / total_time,
            "avg_latency": sum(self.latencies) / len(self.latencies),
            "p90": self.latencies[int(len(self.latencies) * 0.90)],
            "p95": self.latencies[int(len(self.latencies) * 0.95)],
            "p99": self.latencies[int(len(self.latencies) * 0.99)],
            "min_latency": self.latencies[0],
            "max_latency": self.latencies[-1]
        }

    def save_csv(self, filename="results.csv"):
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "status", "latency", "error", "res_size"])
            writer.writeheader()
            writer.writerows(self.results)
            
    def generate_html(self, filename="report.html", stats=None):
        if not stats or "error" in stats: return
        
        # Prepare chart data
        sorted_secs = sorted(self.time_buckets.keys())
        labels = [(s - sorted_secs[0]) for s in sorted_secs] # relative seconds
        reqs_data = [self.time_buckets[s]["reqs"] for s in sorted_secs]
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>ApiStorm Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }}
        .stat-card h3 {{ margin: 0 0 10px 0; color: #7f8c8d; font-size: 14px; text-transform: uppercase; }}
        .stat-card .val {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌩️ ApiStorm Load Test Report</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><h3>Total Requests</h3><div class="val">{stats['total_requests']}</div></div>
            <div class="stat-card"><h3>Error Rate</h3><div class="val" style="color:{'#e74c3c' if stats['total_errors'] > 0 else '#2c3e50'}">{(stats['total_errors']/stats['total_requests']*100):.2f}%</div></div>
            <div class="stat-card"><h3>Avg RPS</h3><div class="val">{stats['rps']:.2f}</div></div>
            <div class="stat-card"><h3>Avg Latency</h3><div class="val">{stats['avg_latency']*1000:.2f} ms</div></div>
            <div class="stat-card"><h3>p95 Latency</h3><div class="val">{stats['p95']*1000:.2f} ms</div></div>
            <div class="stat-card"><h3>p99 Latency</h3><div class="val">{stats['p99']*1000:.2f} ms</div></div>
        </div>

        <div class="chart-container">
            <canvas id="rpsChart"></canvas>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('rpsChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: 'Requests per Second (RPS)',
                    data: {json.dumps(reqs_data)},
                    borderColor: '#3498db',
                    tension: 0.1,
                    fill: false
                }}]
            }},
            options: {{ responsive: true, scales: {{ x: {{ title: {{ display: true, text: 'Time (seconds)' }} }} }} }}
        }});
    </script>
</body>
</html>"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
