import asyncio
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, Any
import uvicorn
import yaml
import psutil

from core.runner import LoadRunner

app = FastAPI(title="ApiStorm UI")

test_status = "idle"
active_runner = None
final_stats = None

@app.get("/")
async def get_ui():
    with open("ui/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/start")
async def start_test(scenario: Dict[str, Any], background_tasks: BackgroundTasks):
    global test_status, active_runner, final_stats
    if test_status == "running":
        return {"error": "Test already running"}
    
    test_status = "running"
    final_stats = None
    
    def run_tests_bg(config_data):
        global test_status, active_runner, final_stats
        
        # We need a new event loop for this background thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        active_runner = LoadRunner(config_data)
        try:
            reporter = loop.run_until_complete(active_runner.run())
            final_stats = reporter.get_final_result()
            # Also generate outputs by default
            reporter.save_csv("ui_output.csv")
            reporter.generate_html("ui_report.html", final_stats)
        except Exception as e:
            print("Error running test:", e)
        finally:
            test_status = "completed"
            loop.close()

    background_tasks.add_task(run_tests_bg, scenario)
    return {"status": "started"}

@app.post("/api/stop")
async def stop_test():
    global test_status, active_runner
    if test_status == "running" and active_runner:
        active_runner.stop_event.set()
        return {"status": "stopping"}
    return {"error": "No test is running"}

@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global test_status, active_runner, final_stats
    try:
        last_status = None
        while True:
            if test_status == "running" and getattr(active_runner, "reporter", None):
                rep = active_runner.reporter
                lats = list(rep.latencies) # Thread-safe shallow copy for safety
                avg_lat = sum(lats) / len(lats) if lats else 0
                payload = {
                    "status": "running",
                    "requests": rep.total_reqs,
                    "errors": rep.total_errors,
                    "rps": len(list(rep.recent_reqs)),
                    "avg_latency": avg_lat * 1000,
                    "ram_usage": psutil.virtual_memory().percent,
                    "cpu_usage": psutil.cpu_percent()
                }
                await websocket.send_json(payload)
                last_status = "running"
            elif test_status == "completed" and last_status == "running":
                # Ensure we send the final completed status once
                payload = final_stats.copy() if final_stats else {}
                if "avg_latency" in payload:
                    payload["avg_latency"] *= 1000
                payload["status"] = "completed"
                payload["ram_usage"] = psutil.virtual_memory().percent
                payload["cpu_usage"] = psutil.cpu_percent()
                await websocket.send_json(payload)
                last_status = "completed"
            elif test_status == "idle":
                # Heartbeat
                pass
                
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("ui:app", host="127.0.0.1", port=8000, reload=True)
