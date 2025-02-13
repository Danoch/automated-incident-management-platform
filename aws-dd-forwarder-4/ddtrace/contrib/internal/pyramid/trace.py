from pyramid.httpexceptions import HTTPException
import pyramid.renderers
from pyramid.settings import asbool
import wrapt

# project
import ddtrace
from ddtrace import config
from ddtrace.constants import _ANALYTICS_SAMPLE_RATE_KEY
from ddtrace.constants import SPAN_KIND
from ddtrace.constants import SPAN_MEASURED_KEY
from ddtrace.contrib import trace_utils
from ddtrace.ext import SpanKind
from ddtrace.ext import SpanTypes
from ddtrace.internal.constants import COMPONENT
from ddtrace.internal.logger import get_logger
from ddtrace.internal.schema import schematize_service_name
from ddtrace.internal.schema import schematize_url_operation
from ddtrace.internal.schema.span_attribute_schema import SpanDirection

from .constants import SETTINGS_ANALYTICS_ENABLED
from .constants import SETTINGS_ANALYTICS_SAMPLE_RATE
from .constants import SETTINGS_DISTRIBUTED_TRACING
from .constants import SETTINGS_SERVICE
from .constants import SETTINGS_TRACE_ENABLED
from .constants import SETTINGS_TRACER


log = get_logger(__name__)

DD_TWEEN_NAME = "ddtrace.contrib.pyramid:trace_tween_factory"
DD_TRACER = "_datadog_tracer"


def trace_pyramid(config):
    config.include("ddtrace.contrib.pyramid")


def includeme(config):
    # Add our tween just before the default exception handler
    config.add_tween(DD_TWEEN_NAME, over=pyramid.tweens.EXCVIEW)
    # ensure we only patch the renderer once.
    if not isinstance(pyramid.renderers.RendererHelper.render, wrapt.ObjectProxy):
        wrapt.wrap_function_wrapper("pyramid.renderers", "RendererHelper.render", trace_render)


def trace_render(func, instance, args, kwargs):
    # If the request is not traced, we do not trace
    request = kwargs.get("request", {})
    if not request:
        log.debug("No request passed to render, will not be traced")
        return func(*args, **kwargs)
    tracer = getattr(request, DD_TRACER, None)
    if not tracer:
        log.debug("No tracer found in request, will not be traced")
        return func(*args, **kwargs)

    with tracer.trace("pyramid.render", span_type=SpanTypes.TEMPLATE) as span:
        span.set_tag_str(COMPONENT, config.pyramid.integration_name)

        return func(*args, **kwargs)


def trace_tween_factory(handler, registry):
    # configuration
    settings = registry.settings
    service = settings.get(SETTINGS_SERVICE) or schematize_service_name("pyramid")
    tracer = settings.get(SETTINGS_TRACER) or ddtrace.tracer
    enabled = asbool(settings.get(SETTINGS_TRACE_ENABLED, tracer.enabled))
    distributed_tracing = asbool(settings.get(SETTINGS_DISTRIBUTED_TRACING, True))

    if enabled:
        # make a request tracing function
        def trace_tween(request):
            trace_utils.activate_distributed_headers(
                tracer, int_config=config.pyramid, request_headers=request.headers, override=distributed_tracing
            )

            span_name = schematize_url_operation("pyramid.request", protocol="http", direction=SpanDirection.INBOUND)
            with tracer.trace(span_name, service=service, resource="404", span_type=SpanTypes.WEB) as span:
                span.set_tag_str(COMPONENT, config.pyramid.integration_name)

                # set span.kind to the type of operation being performed
                span.set_tag_str(SPAN_KIND, SpanKind.SERVER)

                span.set_tag(SPAN_MEASURED_KEY)
                # Configure trace search sample rate
                # DEV: pyramid is special case maintains separate configuration from config api
                analytics_enabled = settings.get(SETTINGS_ANALYTICS_ENABLED)

                if (config._analytics_enabled and analytics_enabled is not False) or analytics_enabled is True:
                    span.set_tag(_ANALYTICS_SAMPLE_RATE_KEY, settings.get(SETTINGS_ANALYTICS_SAMPLE_RATE, True))

                setattr(request, DD_TRACER, tracer)  # used to find the tracer in templates
                response = None
                status = None
                try:
                    response = handler(request)
                except HTTPException as e:
                    # If the exception is a pyramid HTTPException,
                    # that's still valuable information that isn't necessarily
                    # a 500. For instance, HTTPFound is a 302.
                    # As described in docs, Pyramid exceptions are all valid
                    # response types
                    response = e
                    raise
                except BaseException:
                    status = 500
                    raise
                finally:
                    # set request tags
                    if request.matched_route:
                        span.resource = "{} {}".format(request.method, request.matched_route.name)
                        span.set_tag_str("pyramid.route.name", request.matched_route.name)
                    # set response tags
                    if response:
                        status = response.status_code
                        response_headers = response.headers
                    else:
                        response_headers = None

                    trace_utils.set_http_meta(
                        span,
                        config.pyramid,
                        method=request.method,
                        url=request.path_url,
                        status_code=status,
                        query=request.query_string,
                        request_headers=request.headers,
                        response_headers=response_headers,
                        route=request.matched_route.pattern if request.matched_route else None,
                    )
                return response

        return trace_tween

    # if timing support is not enabled, return the original handler
    return handler
