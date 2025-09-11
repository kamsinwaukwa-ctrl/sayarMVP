"""
Prometheus metrics for Sayar WhatsApp Commerce Platform
Provides HTTP request metrics, custom counters, and metrics endpoint
"""

import os
import time
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Info, CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response


# Application info
APP_INFO = Info("sayar_app", "Application information")
APP_INFO.info({
    "version": os.getenv("APP_VERSION", "0.1.0"),
    "service": "sayar-backend"
})

# HTTP Request Metrics (low cardinality labels)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total", 
    "Total HTTP requests",
    ["method", "route", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds", 
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

HTTP_REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight", 
    "HTTP requests currently being processed",
    ["route"]
)

# Authentication Metrics
AUTH_REQUESTS_TOTAL = Counter(
    "auth_requests_total",
    "Total authentication requests", 
    ["endpoint", "result"]  # result: success/failure/rate_limited
)

# Business Metrics
BUSINESS_EVENTS_TOTAL = Counter(
    "business_events_total",
    "Total business domain events",
    ["event_type", "merchant_id"]
)

# Database Metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    "database_connections_active",
    "Active database connections"
)

DB_QUERY_DURATION_SECONDS = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Error Metrics
ERRORS_TOTAL = Counter(
    "errors_total",
    "Total errors by type",
    ["error_type", "component"]
)

# Retry Metrics
RETRY_ATTEMPTS_TOTAL = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["service"]
)

RETRY_FAILURES_TOTAL = Counter(
    "retry_failures_total", 
    "Total retry failures after exhausting attempts",
    ["service"]
)

# Circuit Breaker Metrics
CIRCUIT_BREAKER_OPENS_TOTAL = Counter(
    "circuit_breaker_opens_total",
    "Total circuit breaker opens",
    ["service"]
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service"]
)

# External Service Metrics
EXTERNAL_CALL_DURATION_SECONDS = Histogram(
    "external_call_duration_seconds",
    "External service call duration",
    ["service", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# Outbox Worker Metrics
OUTBOX_JOBS_PROCESSED_TOTAL = Counter(
    "outbox_jobs_processed_total",
    "Total outbox jobs processed",
    ["job_type", "status"]
)

OUTBOX_JOBS_FAILED_TOTAL = Counter(
    "outbox_jobs_failed_total",
    "Total outbox jobs that failed",
    ["job_type", "reason"]
)

DLQ_JOBS_TOTAL = Counter(
    "dlq_jobs_total",
    "Total jobs moved to dead letter queue",
    ["source", "reason"]
)

WORKER_HEARTBEATS_TOTAL = Counter(
    "worker_heartbeats_total",
    "Total worker heartbeats recorded"
)

OUTBOX_FETCH_BATCH_SECONDS = Histogram(
    "outbox_fetch_batch_seconds",
    "Time to fetch batch of outbox jobs",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

JOB_HANDLE_SECONDS = Histogram(
    "job_handle_seconds",
    "Time to handle individual job",
    ["job_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint
    
    Returns:
        Response with Prometheus metrics in text format
    """
    if os.getenv("METRICS_ENABLED", "true").lower() == "false":
        return Response("Metrics disabled", status_code=404)
    
    return Response(
        generate_latest(), 
        media_type=CONTENT_TYPE_LATEST,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


def record_http_request(method: str, route: str, status_code: int, duration_seconds: float):
    """
    Record HTTP request metrics
    
    Args:
        method: HTTP method
        route: Route template (not full URL for low cardinality)
        status_code: HTTP status code
        duration_seconds: Request duration in seconds
    """
    HTTP_REQUESTS_TOTAL.labels(
        method=method, 
        route=route, 
        status_code=str(status_code)
    ).inc()
    
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method, 
        route=route
    ).observe(duration_seconds)


def record_auth_attempt(endpoint: str, result: str):
    """
    Record authentication attempt
    
    Args:
        endpoint: Auth endpoint (login, register, refresh)
        result: Result (success, failure, rate_limited)
    """
    AUTH_REQUESTS_TOTAL.labels(
        endpoint=endpoint,
        result=result
    ).inc()


def record_business_event(event_type: str, merchant_id: Optional[str] = None):
    """
    Record business domain event
    
    Args:
        event_type: Type of business event
        merchant_id: Merchant ID (if applicable)
    """
    BUSINESS_EVENTS_TOTAL.labels(
        event_type=event_type,
        merchant_id=merchant_id or "unknown"
    ).inc()


def record_error(error_type: str, component: str):
    """
    Record application error
    
    Args:
        error_type: Type of error (validation, auth, external_api, etc.)
        component: Component where error occurred
    """
    ERRORS_TOTAL.labels(
        error_type=error_type,
        component=component
    ).inc()


def record_db_query(operation: str, duration_seconds: float):
    """
    Record database query metrics
    
    Args:
        operation: Type of database operation (select, insert, update, delete)
        duration_seconds: Query duration in seconds
    """
    DB_QUERY_DURATION_SECONDS.labels(operation=operation).observe(duration_seconds)


def record_retry_attempt(service: str):
    """
    Record retry attempt
    
    Args:
        service: Service name that is being retried
    """
    RETRY_ATTEMPTS_TOTAL.labels(service=service).inc()


def record_retry_failure(service: str):
    """
    Record retry failure after exhausting all attempts
    
    Args:
        service: Service name that failed
    """
    RETRY_FAILURES_TOTAL.labels(service=service).inc()


def record_circuit_breaker_open(service: str):
    """
    Record circuit breaker opening
    
    Args:
        service: Service name with circuit breaker
    """
    CIRCUIT_BREAKER_OPENS_TOTAL.labels(service=service).inc()


def record_circuit_breaker_state(service: str, state: str):
    """
    Record circuit breaker state
    
    Args:
        service: Service name
        state: Circuit breaker state (closed, half_open, open)
    """
    state_mapping = {"closed": 0, "half_open": 1, "open": 2}
    CIRCUIT_BREAKER_STATE.labels(service=service).set(state_mapping.get(state, 0))


def record_external_call(service: str, endpoint: str, duration_seconds: float):
    """
    Record external service call metrics
    
    Args:
        service: External service name
        endpoint: Service endpoint
        duration_seconds: Call duration in seconds
    """
    EXTERNAL_CALL_DURATION_SECONDS.labels(
        service=service, 
        endpoint=endpoint
    ).observe(duration_seconds)


class HttpMetricsContext:
    """Context manager for HTTP request metrics"""
    
    def __init__(self, method: str, route: str):
        self.method = method
        self.route = route
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        HTTP_REQUESTS_IN_FLIGHT.labels(route=self.route).inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        status_code = 500 if exc_type else 200
        
        record_http_request(self.method, self.route, status_code, duration)
        HTTP_REQUESTS_IN_FLIGHT.labels(route=self.route).dec()


class DbMetricsContext:
    """Context manager for database query metrics"""
    
    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        record_db_query(self.operation, duration)


# Alias for backward compatibility with outbox worker
outbox_jobs_processed_total = OUTBOX_JOBS_PROCESSED_TOTAL
outbox_jobs_failed_total = OUTBOX_JOBS_FAILED_TOTAL
dlq_jobs_total = DLQ_JOBS_TOTAL
worker_heartbeats_total = WORKER_HEARTBEATS_TOTAL
outbox_fetch_batch_seconds = OUTBOX_FETCH_BATCH_SECONDS
job_handle_seconds = JOB_HANDLE_SECONDS