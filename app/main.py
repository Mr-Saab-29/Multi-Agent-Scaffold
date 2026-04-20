import time

from fastapi import FastAPI, Request, Response

from app.api.routes import router as scaffold_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import http_request_latency_seconds, http_requests_total, render_metrics

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(scaffold_router)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    http_requests_total.labels(request.method, path, str(response.status_code)).inc()
    http_request_latency_seconds.labels(request.method, path).observe(elapsed)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")
