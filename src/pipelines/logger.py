"""
Structured Production Logger for NFLPipelines.
Supports dual-output to console (human-readable) and file (JSON Lines for metrics).
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Centralized Log Directory
LOG_DIR = Path("logs/pipelines")
LOG_DIR.mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Format log records as strict JSON for dashboard/monitoring ingestion."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Inject standard extra parameters if supplied
        if hasattr(record, "pipeline_metrics"):
            log_obj.update(record.pipeline_metrics)
            
        if record.exc_info:
            log_obj["error_trace"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def get_pipeline_logger(name: str) -> logging.Logger:
    """
    Creates and configures a production logger that outputs:
    1. INFO+ to Console (with color/formatting)
    2. DEBUG+ to a daily rotating JSONL file for machine analysis
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if instantiated multiple times
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.DEBUG)

    # 1. Console Handler (Human Readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # 2. File Handler (JSON Structured)
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"pipeline_runs_{today_str}.jsonl"
    
    file_handler = logging.FileHandler(str(log_file), mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Do not propagate to root logger
    logger.propagate = False
    
    return logger

class PipelineTimer:
    """Context manager for tracking exactly how long operations take."""
    def __init__(self, operation_name: str, logger: logging.Logger):
        self.operation = operation_name
        self.logger = logger
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.info(f"STARTING: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        metrics = {"duration_seconds": round(duration, 3), "operation": self.operation}
        
        if exc_type:
            self.logger.error(
                f"FAILED: {self.operation} in {duration:.2f}s - {exc_val}", 
                exc_info=True, 
                extra={"pipeline_metrics": metrics}
            )
        else:
            self.logger.info(
                f"COMPLETED: {self.operation} in {duration:.2f}s", 
                extra={"pipeline_metrics": metrics}
            )
