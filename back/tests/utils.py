"""
Test utilities for Sayar WhatsApp Commerce Platform
"""

import json
import logging
from contextlib import contextmanager
from typing import List, Dict, Any
from io import StringIO


class LogCapture:
    """Utility class to capture and parse structured logs during tests"""
    
    def __init__(self):
        self.logs = []
        self.handler = None
        self.stream = None
    
    def start_capture(self):
        """Start capturing logs"""
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setLevel(logging.DEBUG)
        
        # Add handler to root logger to capture all logs
        root_logger = logging.getLogger()
        root_logger.addHandler(self.handler)
        root_logger.setLevel(logging.DEBUG)
    
    def stop_capture(self):
        """Stop capturing logs and parse captured content"""
        if self.handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.handler)
            
            # Parse captured logs
            content = self.stream.getvalue()
            self._parse_logs(content)
            
            self.stream.close()
            self.handler = None
    
    def _parse_logs(self, content: str):
        """Parse log content and extract JSON logs"""
        lines = content.strip().split('\n')
        for line in lines:
            if line.strip():
                try:
                    # Try to parse as JSON (structured logs)
                    log_entry = json.loads(line)
                    self.logs.append(log_entry)
                except json.JSONDecodeError:
                    # If not JSON, treat as plain text log
                    self.logs.append({"message": line, "format": "text"})
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get captured logs"""
        return self.logs
    
    def get_logs_by_event_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get logs filtered by event type"""
        return [log for log in self.logs if log.get("event_type") == event_type]
    
    def get_logs_by_level(self, level: str) -> List[Dict[str, Any]]:
        """Get logs filtered by level"""
        return [log for log in self.logs if log.get("level") == level.upper()]
    
    def clear(self):
        """Clear captured logs"""
        self.logs.clear()


@contextmanager
def capture_logs():
    """
    Context manager to capture logs during test execution
    
    Usage:
        with capture_logs() as log_capture:
            # Your test code here
            logs = log_capture.get_logs()
    """
    log_capture = LogCapture()
    log_capture.start_capture()
    try:
        yield log_capture
    finally:
        log_capture.stop_capture()


def assert_log_contains(logs: List[Dict[str, Any]], **kwargs):
    """
    Assert that logs contain at least one entry matching the given criteria
    
    Args:
        logs: List of log entries
        **kwargs: Key-value pairs to match in log entries
    """
    matching_logs = []
    for log in logs:
        match = True
        for key, value in kwargs.items():
            if log.get(key) != value:
                match = False
                break
        if match:
            matching_logs.append(log)
    
    assert matching_logs, f"No logs found matching criteria: {kwargs}"
    return matching_logs


def assert_log_field_exists(logs: List[Dict[str, Any]], field: str):
    """
    Assert that at least one log entry contains the specified field
    
    Args:
        logs: List of log entries
        field: Field name to check for
    """
    logs_with_field = [log for log in logs if field in log]
    assert logs_with_field, f"No logs found containing field: {field}"
    return logs_with_field


def extract_request_ids(logs: List[Dict[str, Any]]) -> List[str]:
    """
    Extract unique request IDs from log entries
    
    Args:
        logs: List of log entries
        
    Returns:
        List of unique request IDs
    """
    request_ids = set()
    for log in logs:
        if "request_id" in log:
            request_ids.add(log["request_id"])
    return list(request_ids)


def get_metrics_values(metrics_text: str, metric_name: str) -> Dict[str, float]:
    """
    Parse Prometheus metrics text and extract values for a specific metric
    
    Args:
        metrics_text: Raw Prometheus metrics text
        metric_name: Name of the metric to extract
        
    Returns:
        Dictionary mapping metric labels to values
    """
    metrics = {}
    lines = metrics_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith(metric_name):
            # Parse line like: metric_name{label1="value1",label2="value2"} 123.0
            if '{' in line and '}' in line:
                # Extract labels and value
                parts = line.split('}')
                if len(parts) >= 2:
                    labels_part = parts[0] + '}'
                    value_part = parts[1].strip()
                    try:
                        value = float(value_part)
                        metrics[labels_part] = value
                    except ValueError:
                        pass  # Skip invalid values
            elif line.count(' ') >= 1:
                # Simple metric without labels
                parts = line.rsplit(' ', 1)
                try:
                    value = float(parts[1])
                    metrics[metric_name] = value
                except (ValueError, IndexError):
                    pass  # Skip invalid values
    
    return metrics