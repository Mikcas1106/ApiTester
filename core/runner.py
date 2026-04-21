import asyncio
import time
from typing import Dict, Any, List
from .engine import vu_task, data_handler
from .reporter import LiveReporter
import aiohttp

class LoadRunner:
    """Manages the lifecycle of the test, stages, and execution of VUs."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.vus = []
        self.stop_event = asyncio.Event()
        
        data_file = self.config.get("data_file")
        if data_file:
            data_handler.load_data(data_file)

    async def stage_manager(self, session, queue):
        """Linearly scales the number of concurrent VU tasks based on stage targets."""
        stages = self.config.get('stages', [])
        if not stages: # Fallback to a default load test behavior
            stages = [{"duration": 10, "target": 1}] 

        all_tasks = []

        for stage in stages:
            if self.stop_event.is_set():
                break
                
            duration = stage.get('duration', 10)
            target_vus = stage.get('target', 1)
            stage_start = time.time()
            start_vus = len(self.vus)

            while time.time() - stage_start < duration:
                if self.stop_event.is_set():
                    break
                    
                elapsed = time.time() - stage_start
                progress = elapsed / duration
                current_target = int(start_vus + (target_vus - start_vus) * progress)

                # Ramp up
                while len(self.vus) < current_target:
                    vu_stop_event = asyncio.Event()
                    v_id = len(self.vus) + 1
                    task = asyncio.create_task(vu_task(session, self.config, queue, vu_stop_event, v_id))
                    self.vus.append((task, vu_stop_event))
                    all_tasks.append(task)

                # Ramp down
                while len(self.vus) > current_target:
                    task, vu_stop = self.vus.pop()
                    vu_stop.set() # Signals the VU to exit its loop gracefully

                await asyncio.sleep(0.1)

        # Finished all stages. Stop any remaining VUs smoothly.
        for task, vu_stop in self.vus:
            vu_stop.set()
        
        # Await ALL tasks so aiohttp.ClientSession does not abruptly kill the socket pool mid-flight
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
            
        self.stop_event.set()
        await asyncio.sleep(0.2)

    async def run(self):
        """Starts the main session and connects the runner to the reporter."""
        queue = asyncio.Queue()
        self.reporter = LiveReporter(self.config)
        
        # Start the reporter consumer task
        reporter_task = asyncio.create_task(self.reporter.start(queue, self.stop_event))
        
        # TCPConnector tweaking for massive concurrency (bypass limit to let OS decide bounds)
        connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
        async with aiohttp.ClientSession(connector=connector) as session:
            manager_task = asyncio.create_task(self.stage_manager(session, queue))
            
            # Wait for stages to complete execution
            await manager_task
            # Wait for reporter to finish processing remaining queue responses
            await reporter_task
            
        return self.reporter
