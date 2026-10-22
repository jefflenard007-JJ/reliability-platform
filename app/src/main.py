"""shop-api: a small orders service instrumented for observability and chaos testing.

Exposes:
  GET  /healthz              liveness probe
  GET  /readyz               readiness probe
  GET  /orders               list orders
  POST /orders               create an order
  GET  /orders/{order_id}    fetch one order
  GET  /metrics              Prometheus metrics
  POST /chaos                inject latency / errors at runtime (disabled unless CHAOS_ENABLED=true)
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

SERVICE_NAME = os.getenv("SERVICE_NAME", "shop-api")


def chaos_enabled() -> bool:
    return os.getenv("CHAOS_ENABLED", "false").lower() == "true"


# ---------- structured JSON logging (shipped to Loki by Promtail) ----------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger(SERVICE_NAME)
log.handlers = [handler]
log.setLevel(os.getenv("LOG_LEVEL", "INFO"))


# ---------- Prometheus metrics (RED method: Rate, Errors, Duration) ----------
REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0),
)
IN_FLIGHT = Gauge("http_requests_in_flight", "Requests currently being served")
ORDERS_CREATED = Counter("orders_created_total", "Orders successfully created")
CHAOS_STATE = Gauge("chaos_injection_active", "1 when a chaos fault is active", ["fault"])


# ---------- chaos configuration ----------
class ChaosConfig(BaseModel):
    latency_ms: int = Field(0, ge=0, le=10_000, description="Extra latency added to each request")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of requests that return 500")


_chaos = ChaosConfig()
_chaos_lock = Lock()


# ---------- domain ----------
class OrderIn(BaseModel):
    item: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=1, le=1000)


class Order(OrderIn):
    id: str


_orders: dict[str, Order] = {}
_orders_lock = Lock()

app = FastAPI(title=SERVICE_NAME)


def _route_template(request: Request) -> str:
    """Use the route template (/orders/{order_id}) so metrics don't explode in cardinality."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    IN_FLIGHT.inc()
    status = 500
    try:
        if request.url.path not in ("/metrics", "/healthz", "/readyz", "/chaos"):
            with _chaos_lock:
                chaos = _chaos.model_copy()
            if chaos.latency_ms:
                await asyncio.sleep(chaos.latency_ms / 1000)
            if chaos.error_rate and random.random() < chaos.error_rate:
                response = Response("injected fault", status_code=500)
                status = 500
                return response
        response = await call_next(request)
        status = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    finally:
        IN_FLIGHT.dec()
        duration = time.perf_counter() - start
        route = _route_template(request)
        REQUESTS.labels(request.method, route, str(status)).inc()
        LATENCY.labels(request.method, route).observe(duration)
        level = logging.ERROR if status >= 500 else logging.INFO
        log.log(
            level,
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": route,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
            },
        )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/orders")
def list_orders():
    with _orders_lock:
        return list(_orders.values())


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    new = Order(id=str(uuid.uuid4()), **order.model_dump())
    with _orders_lock:
        _orders[new.id] = new
    ORDERS_CREATED.inc()
    return new


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    with _orders_lock:
        order = _orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@app.get("/chaos")
def get_chaos():
    return _chaos


@app.post("/chaos")
def set_chaos(config: ChaosConfig):
    if not chaos_enabled():
        raise HTTPException(status_code=403, detail="chaos endpoint disabled (set CHAOS_ENABLED=true)")
    global _chaos
    with _chaos_lock:
        _chaos = config
    CHAOS_STATE.labels("latency").set(1 if config.latency_ms else 0)
    CHAOS_STATE.labels("errors").set(1 if config.error_rate else 0)
    log.warning(f"chaos updated: latency_ms={config.latency_ms} error_rate={config.error_rate}")
    return _chaos
