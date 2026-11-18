from app.config import get_settings

def configure_telemetry(app) -> None:
    if not get_settings().enable_otel:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        provider = TracerProvider(resource=Resource.create({"service.name": "agentops-ai"}))
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        # Telemetry is optional for local operation.
        return
