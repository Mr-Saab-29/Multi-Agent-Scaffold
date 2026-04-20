from prometheus_client import Counter, Histogram, generate_latest

http_requests_total = Counter(
    "app_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_latency_seconds = Histogram(
    "app_http_request_latency_seconds",
    "HTTP request latency seconds",
    ["method", "path"],
)

runs_total = Counter(
    "app_runs_total",
    "Total scaffold runs",
    ["mode", "status"],
)

llm_calls_total = Counter(
    "app_llm_calls_total",
    "Estimated total LLM calls per completed run",
)


def render_metrics() -> bytes:
    return generate_latest()
