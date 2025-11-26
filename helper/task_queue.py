import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Optional, List
from helper.logger import print_logger

@dataclass
class Task:
    function: Callable
    args: Dict[str, Any]
    batch_id: str
    result: Any = None
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    request_logs: Any = field(default_factory=list)
    api_key: Optional[str] = None
    backend_url: Optional[str] = None
    throttle_time: Optional[int] = None

class TaskQueue:
    def __init__(self, api_key: str, backend_url: str, num_workers: int = 10):
        print_logger(f"Initializing TaskQueue with {num_workers} workers")
        self.queue = queue.Queue()
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.batches: Dict[str, list[str]] = {}  # batch_id -> list of task_ids
        self.processing = False
        self.num_workers = num_workers
        self.worker_threads: List[threading.Thread] = []
        self._lock = threading.Lock()
        self.tabs_api_token = api_key
        self.backend_url = backend_url
        self.task_size = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.pending_tasks = 0

    def is_done(self):
        return self.completed_tasks + self.failed_tasks == self.task_size
        
    def add_task(self, function: Callable, args: Dict[str, Any], batch_id: str, throttle_time: Optional[int] = None) -> str:
        """Add a task to the queue and return its ID"""
        task_id = f"{batch_id}_{len(self.tasks)}"
        task = Task(function=function, args=args, batch_id=batch_id, api_key=self.tabs_api_token, backend_url=self.backend_url, throttle_time=throttle_time)
        
        with self._lock:
            print_logger(f"Adding task {task_id} to batch {batch_id}")
            self.tasks[task_id] = task
            if batch_id not in self.batches:
                self.batches[batch_id] = []
            self.batches[batch_id].append(task_id)
            self.queue.put(task_id)
            print_logger(f"Queue size after adding task: {self.queue.qsize()}")

            self.task_size += 1
            self.pending_tasks += 1
        
        return task_id
    
    def _process_tasks(self):
        """Background thread function to process tasks"""
        thread_name = threading.current_thread().name
        print_logger(f"Starting task processing thread: {thread_name}")
        
        while self.processing:
            try:
                task_id = self.queue.get(timeout=1)
                
                # CRITICAL: Atomic check-and-set to prevent duplicate processing
                with self._lock:
                    task = self.tasks[task_id]
                    if task.status != "pending":
                        # Another thread already claimed this task
                        self.queue.task_done()
                        continue
                    task.status = "running"
                    self.pending_tasks -= 1
                
                # Now we own this task exclusively
                print_logger(f"{thread_name} processing task {task_id} from batch {task.batch_id}")
                
                try:
                    print_logger(f"Executing function for task {task_id} with args: {task.args}")
                    task.args["task"] = task
                    result = task.function(**task.args)
                    
                    # Update result (brief lock for thread safety)
                    with self._lock:
                        task.result = result
                        task.status = "completed" if result is not None else "failed"
                        self.completed_tasks += 1
                    
                    if result is None:
                        print_logger(f"Task {task_id} failed with result: {result}")
                    else:
                        print_logger(f"Task {task_id} completed successfully with result: {result}")
                        
                except Exception as e:
                    with self._lock:
                        task.status = "failed"
                        task.error = str(e)
                        task.result = f"Failed to execute function {str(e)}"
                        self.failed_tasks += 1
                    print_logger(f"Task {task_id} failed with error: {str(e)}")
                
                # Handle throttling
                if task.throttle_time:
                    print_logger(f"Sleeping for {task.throttle_time} seconds")
                    time.sleep(task.throttle_time) # Built in buffer of 1 second to avoid rate limiting

                
                self.queue.task_done()
                print_logger(f"Queue size after task completion: {self.queue.qsize()}")
                
            except queue.Empty:
                continue
        print_logger(f"Task processing thread stopped: {thread_name}")
    
    def start_processing(self):
        """Start multiple background processing threads"""
        if not self.processing:
            print_logger(f"Starting queue processing with {self.num_workers} workers")
            self.processing = True
            self.worker_threads = []
            
            for i in range(self.num_workers):
                worker = threading.Thread(target=self._process_tasks, name=f"Worker-{i}")
                worker.daemon = True
                worker.start()
                self.worker_threads.append(worker)
            
            print_logger("Queue processing started")
    
    def stop_processing(self):
        """Stop all background processing threads"""
        if self.processing:
            print_logger("Stopping queue processing")
            self.processing = False
            
            for worker in self.worker_threads:
                worker.join()
            self.worker_threads = []
            print_logger("Queue processing stopped")
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get current queue statistics"""
        with self._lock:
            total = len(self.tasks)
            completed = sum(1 for task in self.tasks.values() if task.status == "completed")
            failed = sum(1 for task in self.tasks.values() if task.status == "failed")
            pending = sum(1 for task in self.tasks.values() if task.status == "pending")
            running = sum(1 for task in self.tasks.values() if task.status == "running")
            
            stats = {
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "running": running,
                "queue_size": self.queue.qsize()
            }
            print_logger(f"Queue stats: {stats}")
            return stats
    
    def get_batch_stats(self, batch_id: str) -> Dict[str, int]:
        """Get statistics for a specific batch"""
        if batch_id not in self.batches:
            print_logger(f"No batch found with ID: {batch_id}")
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0, "running": 0}
        
        with self._lock:
            batch_tasks = [self.tasks[task_id] for task_id in self.batches[batch_id]]
            total = len(batch_tasks)
            completed = sum(1 for task in batch_tasks if task.status == "completed")
            failed = sum(1 for task in batch_tasks if task.status == "failed")
            pending = sum(1 for task in batch_tasks if task.status == "pending")
            running = sum(1 for task in batch_tasks if task.status == "running")
            
            stats = {
                "total": total,
                "completed": completed,
                "failed": failed,
                "pending": pending,
                "running": running
            }
            print_logger(f"Batch {batch_id} stats: {stats}")
            return stats 
        
    def get_batch_results(self, batch_id: str) -> List[Any]:
        """Get results for a specific batch"""
        if batch_id not in self.batches:
            print_logger(f"No batch found with ID: {batch_id}")
            return []
        return [self.tasks[task_id].result for task_id in self.batches[batch_id]]