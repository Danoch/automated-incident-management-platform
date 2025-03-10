from collections import deque

from tornado.web import HTTPError

from ddtrace import config
from ddtrace.constants import _ANALYTICS_SAMPLE_RATE_KEY
from ddtrace.constants import SPAN_KIND
from ddtrace.constants import SPAN_MEASURED_KEY
from ddtrace.contrib import trace_utils
from ddtrace.contrib.trace_utils import set_http_meta
from ddtrace.ext import SpanKind
from ddtrace.ext import SpanTypes
from ddtrace.internal.constants import COMPONENT
from ddtrace.internal.schema import schematize_url_operation
from ddtrace.internal.schema.span_attribute_schema import SpanDirection
from ddtrace.internal.utils import ArgumentError
from ddtrace.internal.utils import get_argument_value

from .constants import CONFIG_KEY
from .constants import REQUEST_SPAN_KEY
from .stack_context import TracerStackContext


def execute(func, handler, args, kwargs):
    """
    Wrap the handler execute method so that the entire request is within the same
    ``TracerStackContext``. This simplifies users code when the automatic ``Context``
    retrieval is used via ``Tracer.trace()`` method.
    """
    # retrieve tracing settings
    settings = handler.settings[CONFIG_KEY]
    tracer = settings["tracer"]
    service = settings["default_service"]
    distributed_tracing = settings["distributed_tracing"]

    with TracerStackContext():
        trace_utils.activate_distributed_headers(
            tracer, int_config=config.tornado, request_headers=handler.request.headers, override=distributed_tracing
        )

        # store the request span in the request so that it can be used later
        request_span = tracer.trace(
            schematize_url_operation("tornado.request", protocol="http", direction=SpanDirection.INBOUND),
            service=service,
            span_type=SpanTypes.WEB,
        )

        request_span.set_tag_str(COMPONENT, config.tornado.integration_name)

        # set span.kind to the type of operation being performed
        request_span.set_tag_str(SPAN_KIND, SpanKind.SERVER)

        request_span.set_tag(SPAN_MEASURED_KEY)
        # set analytics sample rate
        # DEV: tornado is special case maintains separate configuration from config api
        analytics_enabled = settings["analytics_enabled"]
        if (config._analytics_enabled and analytics_enabled is not False) or analytics_enabled is True:
            request_span.set_tag(_ANALYTICS_SAMPLE_RATE_KEY, settings.get("analytics_sample_rate", True))

        http_route = _find_route(handler.application.default_router.rules, handler.request)
        if http_route is not None and isinstance(http_route, str):
            request_span.set_tag_str("http.route", http_route)
        setattr(handler.request, REQUEST_SPAN_KEY, request_span)

        return func(*args, **kwargs)


def _find_route(initial_rule_set, request):
    """
    We have to walk through the same chain of rules that tornado does to find a matching rule.
    """
    rules = deque()

    for rule in initial_rule_set:
        rules.append(rule)

    while len(rules) > 0:
        rule = rules.popleft()
        if rule.matcher.match(request) is not None:
            if hasattr(rule.matcher, "_path"):
                return rule.matcher._path
            elif hasattr(rule.target, "rules"):
                rules.extendleft(rule.target.rules)

    return "^$"


def on_finish(func, handler, args, kwargs):
    """
    Wrap the ``RequestHandler.on_finish`` method. This is the last executed method
    after the response has been sent, and it's used to retrieve and close the
    current request span (if available).
    """
    request = handler.request
    request_span = getattr(request, REQUEST_SPAN_KEY, None)
    if request_span:
        # use the class name as a resource; if an handler is not available, the
        # default handler class will be used so we don't pollute the resource
        # space here
        klass = handler.__class__
        request_span.resource = "{}.{}".format(klass.__module__, klass.__name__)
        set_http_meta(
            request_span,
            config.tornado,
            method=request.method,
            url=request.full_url().rsplit("?", 1)[0],
            status_code=handler.get_status(),
            query=request.query,
        )
        request_span.finish()

    return func(*args, **kwargs)


def log_exception(func, handler, args, kwargs):
    """
    Wrap the ``RequestHandler.log_exception``. This method is called when an
    Exception is not handled in the user code. In this case, we save the exception
    in the current active span. If the Tornado ``Finish`` exception is raised, this wrapper
    will not be called because ``Finish`` is not an exception.
    """
    # safe-guard: expected arguments -> log_exception(self, typ, value, tb)
    try:
        value = get_argument_value(args, kwargs, 1, "value")
    except ArgumentError:
        value = None

    if not value:
        return func(*args, **kwargs)

    # retrieve the current span
    tracer = handler.settings[CONFIG_KEY]["tracer"]
    current_span = tracer.current_span()

    if not current_span:
        return func(*args, **kwargs)

    if isinstance(value, HTTPError):
        # Tornado uses HTTPError exceptions to stop and return a status code that
        # is not a 2xx. In this case we want to check the status code to be sure that
        # only 5xx are traced as errors, while any other HTTPError exception is handled as
        # usual.
        if config.http_server.is_error_code(value.status_code):
            current_span.set_exc_info(*args)
    else:
        # any other uncaught exception should be reported as error
        current_span.set_exc_info(*args)

    return func(*args, **kwargs)
