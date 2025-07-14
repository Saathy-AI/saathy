"""OpenTelemetry configuration for Saathy."""

import logging
from logging.config import dictConfig

import structlog
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from saathy.config import Settings

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    """Configure structured logging with structlog."""
    if not settings.enable_tracing:
        # Use a simpler logging config if tracing is disabled
        log_level = settings.log_level.upper()
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info("Configured basic logging with level %s.", log_level)
        return

    LoggingInstrumentor().instrument(
        tracer_provider=trace.get_tracer_provider(), set_logging_format=True
    )

    log_level = settings.log_level.upper()

    # Shared processors for both environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        # JSON logs for production
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        # Colored console logs for development
        processors = shared_processors + [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": (
                    structlog.dev.ConsoleRenderer()
                    if not settings.is_production
                    else structlog.processors.JSONRenderer()
                ),
                "foreign_pre_chain": shared_processors,
            },
        },
        "handlers": {
            "default": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "": {"handlers": ["default"], "level": log_level, "propagate": True},
            "uvicorn.error": {"level": "INFO", "propagate": True},
            "uvicorn.access": {"handlers": [], "propagate": False},
        },
    }
    dictConfig(log_config)
    logger.info(
        "Configured structured logging with level %s for %s environment.",
        log_level,
        settings.environment,
    )


def configure_tracing(settings: Settings, app) -> None:
    """Configure OpenTelemetry tracing for the FastAPI application."""
    if not settings.enable_tracing:
        logger.info("Skipping OpenTelemetry tracing configuration (disabled).")
        return

    resource = Resource.create({"service.name": settings.service_name})

    # Determine sampler based on environment
    sampler = (
        TraceIdRatioBased(1.0) if settings.is_development else TraceIdRatioBased(0.1)
    )

    provider = TracerProvider(resource=resource, sampler=sampler)
    trace.set_tracer_provider(provider)

    # Console exporter for local development
    if settings.is_development:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(console_exporter))
        logger.info("Configured ConsoleSpanExporter for local development.")

    # Jaeger exporter for production-like environments
    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.jaeger_agent_host,
            agent_port=settings.jaeger_agent_port,
        )
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        logger.info(
            "Configured JaegerExporter to %s:%s",
            settings.jaeger_agent_host,
            settings.jaeger_agent_port,
        )
    except Exception as e:
        logger.error("Failed to configure JaegerExporter: %s", e, exc_info=True)
        logger.warning("Tracing will proceed without Jaeger exporter.")

    # Instrument FastAPI application
    excluded_endpoints = ["/healthz", "/metrics"]
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=",".join(excluded_endpoints),
        tracer_provider=provider,
    )

    logger.info(
        "Successfully configured OpenTelemetry tracing for service: %s",
        settings.service_name,
    )
