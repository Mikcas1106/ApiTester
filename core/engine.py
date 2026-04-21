import asyncio
import time
import csv
import itertools
from typing import Dict, Any

class DataHandler:
    """Manages reading from CSV files for data-driven testing"""
    def __init__(self, filepath: str = None):
        self.data_pool = []
        self.iterator = None
        if filepath:
            self.load_data(filepath)

    def load_data(self, filepath: str):
        try:
            with open(filepath, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.data_pool = list(reader)
            if self.data_pool:
                self.iterator = itertools.cycle(self.data_pool)
        except Exception as e:
            print(f"Failed to load data file: {e}")

    def get_next(self):
        return next(self.iterator) if self.iterator else {}

# Initialize a global instance of DataHandler for VUs
data_handler = DataHandler()

async def vu_task(session, config: Dict[str, Any], queue: asyncio.Queue, stop_event: asyncio.Event, vu_id: int):
    """A Virtual User (VU) loop that executes requests based on the scenario config"""
    
    base_url = config.get("target_url")
    method = config.get("method", "GET").upper()
    headers_template = config.get("headers", {})
    payload_template = config.get("payload", None)
    think_time = config.get("think_time", 0)

    # Fast validation
    if not base_url:
        raise ValueError("target_url missing in config")

    while not stop_event.is_set():
        # Inject data-driven variables if CSV data exists
        context = data_handler.get_next()
        
        # Simple variable substitution for paths
        target_url = base_url.format(**context) if context else base_url
        
        headers = headers_template.copy() if headers_template else {}
        for k, v in headers.items():
            if isinstance(v, str) and context:
                headers[k] = v.format(**context)
                
        payload = payload_template.copy() if payload_template and isinstance(payload_template, dict) else payload_template

        start = time.perf_counter()
        status = 0
        error = None
        res_size = 0
        
        try:
            async with session.request(method, target_url, headers=headers, json=payload) as response:
                content = await response.read()
                status = response.status
                res_size = len(content)
        except Exception as e:
            error = str(e)
            
        latency = time.perf_counter() - start
        
        # Send result to the Reporter queue
        await queue.put({
            "timestamp": time.time(),
            "status": status,
            "latency": latency,
            "error": error,
            "res_size": res_size
        })

        if think_time > 0 and not stop_event.is_set():
            await asyncio.sleep(think_time)
