from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import Request

from app.core.logging_support import span_id_ctx, trace_id_ctx
from app.core.observability_privacy import sanitize_observability_value
from app.core.settings import Settings, get_settings

try:
    from opentelemetry import propagate, trace
    from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, SERVICE_NAMESPACE, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import SpanKind, Status, StatusCode
except Exception:  # pragma: no cover - dependência opcional no runtime de desenvolvimento
    propagate = None
    trace = None
    Resource = None
    TracerProvider = None
    BatchSpanProcessor = None
    ConsoleSpanExporter = None
    SpanKind = None
    Status = None
    StatusCode = None


logger = logging.getLogger("tariel.telemetry")
_TRACER_PROVIDER_READY = False
_SENTRY_READY = False


def observability_runtime_snapshot(settings: Settings | None = None) -> dict[str, Any]:
    current = settings or get_settings()
    return {
        "environment": current.ambiente,
        "release": current.observability_release,
        "correlation_header_name": current.observability_header_name,
        "client_request_header_name": current.observability_client_request_header_name,
        "trace_header_name": current.observability_trace_header_name,
        "traceparent_header_name": "traceparent",
        "otel": {
            "enabled": bool(current.otel_enabled and trace is not None),
            "exporter_mode": current.otel_exporter_mode,
            "otlp_endpoint_configured": bool(current.otel_otlp_endpoint),
            "service_name": current.otel_service_name,
            "service_namespace": current.otel_service_namespace,
        },
        "sentry": {
            "enabled": bool(current.sentry_enabled),
            "send_default_pii": bool(current.sentry_send_default_pii),
            "traces_sample_rate": float(current.sentry_traces_sample_rate),
            "profiles_sample_rate": float(current.sentry_profiles_sample_rate),
        },
        "client_policy": {
            "browser_analytics_enabled": bool(current.browser_analytics_enabled),
            "browser_replay_enabled": bool(current.browser_replay_enabled),
            "mobile_analytics_opt_in_required": bool(current.mobile_analytics_opt_in_required),
        },
        "retention": {
            "log_days": int(current.observability_log_retention_days),
            "perf_days": int(current.observability_perf_retention_days),
            "artifact_days": int(current.observability_artifact_retention_days),
        },
    }


def _load_otlp_exporter() -> Any | None:
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter
    except Exception:
        return None


def _ensure_tracer_provider(settings: Settings) -> None:
    global _TRACER_PROVIDER_READY
    if _TRACER_PROVIDER_READY or not settings.otel_enabled or trace is None or TracerProvider is None or Resource is None:
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.otel_service_name,
            SERVICE_NAMESPACE: settings.otel_service_namespace,
            SERVICE_VERSION: settings.observability_release,
            DEPLOYMENT_ENVIRONMENT: settings.ambiente,
        }
    )
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_mode == "console" and BatchSpanProcessor is not None and ConsoleSpanExporter is not None:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    elif settings.otel_exporter_mode == "otlp" and BatchSpanProcessor is not None and settings.otel_otlp_endpoint:
        exporter_cls = _load_otlp_exporter()
        if exporter_cls is not None:
            provider.add_span_processor(
                BatchSpanProcessor(
                    exporter_cls(
                        endpoint=settings.otel_otlp_endpoint,
                        timeout=settings.otel_export_timeout_ms,
                    )
                )
            )
        else:
            logger.warning(
                "OTLP exporter indisponível; mantendo tracing local sem export",
                extra={"endpoint": settings.otel_otlp_endpoint},
            )

    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER_READY = True


def configure_telemetry_runtime(*, settings: Settings | None = None) -> dict[str, Any]:
    current = settings or get_settings()
    _ensure_tracer_provider(current)
    return observability_runtime_snapshot(current)


def _sentry_before_send(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    return sanitize_observability_value(event)


def configure_sentry_runtime(*, settings: Settings | None = None) -> dict[str, Any]:
    global _SENTRY_READY
    current = settings or get_settings()
    if _SENTRY_READY or not current.sentry_enabled:
        return observability_runtime_snapshot(current)

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=current.sentry_dsn,
            environment=current.ambiente,
            release=current.observability_release,
            send_default_pii=current.sentry_send_default_pii,
            traces_sample_rate=current.sentry_traces_sample_rate,
            profiles_sample_rate=current.sentry_profiles_sample_rate,
            integrations=[FastApiIntegration()],
            before_send=_sentry_before_send,
        )
        _SENTRY_READY = True
    except Exception:
        logger.exception("Falha ao inicializar Sentry")

    return observability_runtime_snapshot(current)


def get_current_trace_context() -> dict[str, str] | None:
    if trace is None:
        return None

    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()
    if not span_context or not span_context.is_valid:
        return None

    trace_id = f"{span_context.trace_id:032x}"
    span_id = f"{span_context.span_id:016x}"
    trace_flags = "01" if int(span_context.trace_flags) else "00"
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "traceparent": f"00-{trace_id}-{span_id}-{trace_flags}",
    }


def sync_trace_context_to_request(request: Request | None) -> dict[str, str] | None:
    snapshot = get_current_trace_context()
    if snapshot is None:
        return None

    trace_id_ctx.set(snapshot["trace_id"])
    span_id_ctx.set(snapshot["span_id"])

    if request is not None:
        request.state.trace_id = snapshot["trace_id"]
        request.state.span_id = snapshot["span_id"]
        request.state.traceparent = snapshot["traceparent"]

    return snapshot


@contextmanager
def start_request_trace(
    *,
    request: Request,
    span_name: str,
    correlation_id: str,
    request_id: str,
    client_request_id: str | None = None,
) -> Iterator[dict[str, str] | None]:
    settings = get_settings()
    if not settings.otel_enabled or trace is None or propagate is None or SpanKind is None:
        yield None
        return

    _ensure_tracer_provider(settings)
    tracer = trace.get_tracer(settings.otel_service_name)
    carrier = {key: value for key, value in request.headers.items()}
    extracted_context = propagate.extract(carrier)

    with tracer.start_as_current_span(
        span_name,
        context=extracted_context,
        kind=SpanKind.SERVER,
    ) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.target", request.url.path)
        span.set_attribute("tariel.correlation_id", correlation_id)
        span.set_attribute("tariel.request_id", request_id)
        if client_request_id:
            span.set_attribute("tariel.client_request_id", client_request_id)
        snapshot = sync_trace_context_to_request(request)
        yield snapshot


@contextmanager
def start_operation_trace(
    category: str,
    name: str,
    *,
    detail: dict[str, Any] | None = None,
) -> Iterator[dict[str, str] | None]:
    settings = get_settings()
    if not settings.otel_enabled or trace is None:
        yield None
        return

    _ensure_tracer_provider(settings)
    tracer = trace.get_tracer(settings.otel_service_name)
    span_name = f"{category}:{name}"
    with tracer.start_as_current_span(span_name, kind=SpanKind.INTERNAL) as span:
        span.set_attribute("tariel.operation.category", str(category or "function"))
        span.set_attribute("tariel.operation.name", str(name or "operacao"))
        if detail:
            span.set_attribute(
                "tariel.operation.detail",
                str(sanitize_observability_value(detail)),
            )
        snapshot = get_current_trace_context()
        if snapshot is not None:
            trace_id_ctx.set(snapshot["trace_id"])
            span_id_ctx.set(snapshot["span_id"])
        yield snapshot


def mark_current_span_success(status_code: int) -> dict[str, str] | None:
    snapshot = get_current_trace_context()
    if trace is None:
        return snapshot
    current_span = trace.get_current_span()
    if snapshot is not None and current_span is not None:
        current_span.set_attribute("http.status_code", int(status_code))
    return snapshot


def mark_current_span_exception(exc: Exception, *, status_code: int = 500) -> dict[str, str] | None:
    snapshot = get_current_trace_context()
    if trace is None or Status is None or StatusCode is None:
        return snapshot

    current_span = trace.get_current_span()
    if current_span is not None:
        current_span.record_exception(exc)
        current_span.set_status(Status(StatusCode.ERROR, str(exc)))
        current_span.set_attribute("http.status_code", int(status_code))
    return snapshot


def capture_exception_for_observability(
    exc: Exception,
    *,
    request: Request | None = None,
) -> None:
    settings = get_settings()
    if not settings.sentry_enabled:
        return

    try:
        import sentry_sdk
    except Exception:
        return

    with sentry_sdk.push_scope() as scope:
        if request is not None:
            scope.set_tag("correlation_id", getattr(request.state, "correlation_id", None))
            scope.set_tag("trace_id", getattr(request.state, "trace_id", None))
            scope.set_context(
                "request_runtime",
                sanitize_observability_value(
                    {
                        "path": request.url.path,
                        "method": request.method,
                        "correlation_id": getattr(request.state, "correlation_id", None),
                        "trace_id": getattr(request.state, "trace_id", None),
                    }
                ),
            )
        sentry_sdk.capture_exception(exc)


__all__ = [
    "capture_exception_for_observability",
    "configure_sentry_runtime",
    "configure_telemetry_runtime",
    "get_current_trace_context",
    "mark_current_span_exception",
    "mark_current_span_success",
    "observability_runtime_snapshot",
    "start_operation_trace",
    "start_request_trace",
    "sync_trace_context_to_request",
]
