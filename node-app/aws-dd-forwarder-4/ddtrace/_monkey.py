import importlib
import os
import threading
from typing import TYPE_CHECKING  # noqa:F401

from wrapt.importer import when_imported

from ddtrace.appsec import load_common_appsec_modules

from .appsec._iast._utils import _is_iast_enabled
from .internal import telemetry
from .internal.logger import get_logger
from .internal.utils import formats
from .settings import _config as config


if TYPE_CHECKING:  # pragma: no cover
    from typing import Any  # noqa:F401
    from typing import Callable  # noqa:F401
    from typing import List  # noqa:F401
    from typing import Union  # noqa:F401


log = get_logger(__name__)

# Default set of modules to automatically patch or not
PATCH_MODULES = {
    "aioredis": True,
    "aiomysql": True,
    "aredis": True,
    "asyncio": True,
    "avro": True,
    "boto": True,
    "botocore": True,
    "bottle": True,
    "cassandra": True,
    "celery": True,
    "consul": True,
    "django": True,
    "dramatiq": True,
    "elasticsearch": True,
    "algoliasearch": True,
    "futures": True,
    "google_generativeai": True,
    "gevent": True,
    "graphql": True,
    "grpc": True,
    "httpx": True,
    "kafka": True,
    "mongoengine": True,
    "mysql": True,
    "mysqldb": True,
    "pymysql": True,
    "mariadb": True,
    "psycopg": True,
    "pylibmc": True,
    "pymemcache": True,
    "pymongo": True,
    "redis": True,
    "rediscluster": True,
    "requests": True,
    "rq": True,
    "sanic": True,
    "snowflake": False,
    "sqlalchemy": False,  # Prefer DB client instrumentation
    "sqlite3": True,
    "aiohttp": True,  # requires asyncio (Python 3.4+)
    "aiohttp_jinja2": True,
    "aiopg": True,
    "aiobotocore": False,
    "httplib": False,
    "urllib3": False,
    "vertica": True,
    "molten": True,
    "jinja2": True,
    "mako": True,
    "flask": True,
    "kombu": False,
    "starlette": True,
    # Ignore some web framework integrations that might be configured explicitly in code
    "falcon": True,
    "pyramid": True,
    # Auto-enable logging if the environment variable DD_LOGS_INJECTION is true
    "logbook": config._logs_injection,  # type: ignore
    "logging": config._logs_injection,  # type: ignore
    "loguru": config._logs_injection,  # type: ignore
    "structlog": config._logs_injection,  # type: ignore
    "pynamodb": True,
    "pyodbc": True,
    "fastapi": True,
    "dogpile_cache": True,
    "yaaredis": True,
    "asyncpg": True,
    "aws_lambda": True,  # patch only in AWS Lambda environments
    "tornado": False,
    "openai": True,
    "langchain": True,
    "anthropic": True,
    "subprocess": True,
    "unittest": True,
    "coverage": False,
}


# this information would make sense to live in the contrib modules,
# but that would mean getting it would require importing those modules,
# which we need to avoid until as late as possible.
CONTRIB_DEPENDENCIES = {
    "tornado": ("futures",),
}


_LOCK = threading.Lock()
_PATCHED_MODULES = set()

# Module names that need to be patched for a given integration. If the module
# name coincides with the integration name, then there is no need to add an
# entry here.
_MODULES_FOR_CONTRIB = {
    "elasticsearch": (
        "elasticsearch",
        "elasticsearch1",
        "elasticsearch2",
        "elasticsearch5",
        "elasticsearch6",
        "elasticsearch7",
        # Starting with version 8, the default transport which is what we
        # actually patch is found in the separate elastic_transport package
        "elastic_transport",
        "opensearchpy",
    ),
    "psycopg": (
        "psycopg",
        "psycopg2",
    ),
    "snowflake": ("snowflake.connector",),
    "cassandra": ("cassandra.cluster",),
    "dogpile_cache": ("dogpile.cache",),
    "mysqldb": ("MySQLdb",),
    "futures": ("concurrent.futures.thread",),
    "vertica": ("vertica_python",),
    "aws_lambda": ("datadog_lambda",),
    "httplib": ("http.client",),
    "kafka": ("confluent_kafka",),
    "google_generativeai": ("google.generativeai",),
}


DEFAULT_MODULES_PREFIX = "ddtrace.contrib"


class PatchException(Exception):
    """Wraps regular `Exception` class when patching modules"""

    pass


class ModuleNotFoundException(PatchException):
    pass


def _on_import_factory(module, prefix="ddtrace.contrib", raise_errors=True, patch_indicator=True):
    # type: (str, str, bool, Union[bool, List[str]]) -> Callable[[Any], None]
    """Factory to create an import hook for the provided module name"""

    def on_import(hook):
        # Import and patch module
        path = "%s.%s" % (prefix, module)
        try:
            imported_module = importlib.import_module(path)
        except Exception as e:
            if raise_errors:
                raise
            error_msg = "failed to import ddtrace module %r when patching on import" % (path,)
            log.error(error_msg, exc_info=True)
            telemetry.telemetry_writer.add_integration(module, False, PATCH_MODULES.get(module) is True, error_msg)
            telemetry.telemetry_writer.add_count_metric(
                "tracers", "integration_errors", 1, (("integration_name", module), ("error_type", type(e).__name__))
            )
        else:
            imported_module.patch()
            if hasattr(imported_module, "get_versions"):
                versions = imported_module.get_versions()
                for name, v in versions.items():
                    telemetry.telemetry_writer.add_integration(
                        name, True, PATCH_MODULES.get(module) is True, "", version=v
                    )
            else:
                version = imported_module.get_version()
                telemetry.telemetry_writer.add_integration(
                    module, True, PATCH_MODULES.get(module) is True, "", version=version
                )

            if hasattr(imported_module, "patch_submodules"):
                imported_module.patch_submodules(patch_indicator)

    return on_import


def patch_all(**patch_modules):
    # type: (bool) -> None
    """Automatically patches all available modules.

    In addition to ``patch_modules``, an override can be specified via an
    environment variable, ``DD_TRACE_<module>_ENABLED`` for each module.

    ``patch_modules`` have the highest precedence for overriding.

    :param dict patch_modules: Override whether particular modules are patched or not.

        >>> patch_all(redis=False, cassandra=False)
    """
    modules = PATCH_MODULES.copy()

    # The enabled setting can be overridden by environment variables
    for module, _enabled in modules.items():
        env_var = "DD_TRACE_%s_ENABLED" % module.upper()
        if env_var in os.environ:
            modules[module] = formats.asbool(os.environ[env_var])

        # Enable all dependencies for the module
        if modules[module]:
            for dep in CONTRIB_DEPENDENCIES.get(module, ()):
                modules[dep] = True

    # Arguments take precedence over the environment and the defaults.
    modules.update(patch_modules)

    patch(raise_errors=False, **modules)
    if _is_iast_enabled():
        from ddtrace.appsec._iast._patch_modules import patch_iast
        from ddtrace.appsec.iast import enable_iast_propagation

        patch_iast()
        enable_iast_propagation()

    load_common_appsec_modules()


def patch(raise_errors=True, patch_modules_prefix=DEFAULT_MODULES_PREFIX, **patch_modules):
    # type: (bool, str, Union[List[str], bool]) -> None
    """Patch only a set of given modules.

    :param bool raise_errors: Raise error if one patch fail.
    :param dict patch_modules: List of modules to patch.

        >>> patch(psycopg=True, elasticsearch=True)
    """
    contribs = {c: patch_indicator for c, patch_indicator in patch_modules.items() if patch_indicator}
    for contrib, patch_indicator in contribs.items():
        # Check if we have the requested contrib.
        if not os.path.isfile(os.path.join(os.path.dirname(__file__), "contrib", contrib, "__init__.py")):
            if raise_errors:
                raise ModuleNotFoundException(
                    "integration module ddtrace.contrib.%s does not exist, "
                    "module will not have tracing available" % contrib
                )
        modules_to_patch = _MODULES_FOR_CONTRIB.get(contrib, (contrib,))
        for module in modules_to_patch:
            # Use factory to create handler to close over `module` and `raise_errors` values from this loop
            when_imported(module)(
                _on_import_factory(contrib, raise_errors=raise_errors, patch_indicator=patch_indicator)
            )

        # manually add module to patched modules
        with _LOCK:
            _PATCHED_MODULES.add(contrib)

    log.info(
        "Configured ddtrace instrumentation for %s integration(s). The following modules have been patched: %s",
        len(contribs),
        ",".join(contribs),
    )


def _get_patched_modules():
    # type: () -> List[str]
    """Get the list of patched modules"""
    with _LOCK:
        return sorted(_PATCHED_MODULES)
