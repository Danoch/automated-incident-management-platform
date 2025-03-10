import dataclasses
import typing as t

from ddtrace.ext.test_visibility._utils import _catch_and_log_exceptions
import ddtrace.ext.test_visibility.api as ext_api
from ddtrace.internal import core
from ddtrace.internal.logger import get_logger
from ddtrace.internal.test_visibility._internal_item_ids import InternalTestId


log = get_logger(__name__)


@dataclasses.dataclass
class AutoTestRetriesSettings:
    enabled: bool = False
    max_retries: int = 5
    max_session_total_retries: int = 1000


class ATRSessionMixin:
    @staticmethod
    @_catch_and_log_exceptions
    def atr_is_enabled() -> bool:
        log.debug("Checking if Auto Test Retries is enabled for session")
        is_enabled = core.dispatch_with_results("test_visibility.atr.is_enabled").is_enabled.value
        log.debug("Auto Test Retries enabled: %s", is_enabled)
        return is_enabled

    @staticmethod
    @_catch_and_log_exceptions
    def atr_has_failed_tests() -> bool:
        log.debug("Checking if session has failed tests for Auto Test Retries")
        has_failed_tests = core.dispatch_with_results(
            "test_visibility.atr.session_has_failed_tests"
        ).has_failed_tests.value
        log.debug("Session has ATR failed tests: %s", has_failed_tests)
        return has_failed_tests


class ATRTestMixin:
    @staticmethod
    @_catch_and_log_exceptions
    def atr_should_retry(item_id: InternalTestId) -> bool:
        log.debug("Checking if item %s should be retried for Auto Test Retries", item_id)
        should_retry_test = core.dispatch_with_results(
            "test_visibility.atr.should_retry_test", (item_id,)
        ).should_retry_test.value
        log.debug("Item %s should be retried: %s", item_id, should_retry_test)
        return should_retry_test

    @staticmethod
    @_catch_and_log_exceptions
    def atr_add_retry(item_id: InternalTestId, start_immediately: bool = False) -> int:
        log.debug("Adding Auto Test Retries retry for item %s", item_id)
        retry_number = core.dispatch_with_results(
            "test_visibility.atr.add_retry", (item_id, start_immediately)
        ).retry_number.value
        log.debug("Added Auto Test Retries retry %s for item %s", retry_number, item_id)
        return retry_number

    @staticmethod
    @_catch_and_log_exceptions
    def atr_start_retry(item_id: InternalTestId) -> None:
        log.debug("Starting retry for item %s", item_id)
        core.dispatch("test_visibility.atr.start_retry", (item_id,))

    class ATRRetryFinishArgs(t.NamedTuple):
        test_id: InternalTestId
        retry_number: int
        status: ext_api.TestStatus
        skip_reason: t.Optional[str] = None
        exc_info: t.Optional[ext_api.TestExcInfo] = None

    @staticmethod
    @_catch_and_log_exceptions
    def atr_finish_retry(
        item_id: InternalTestId,
        retry_number: int,
        status: ext_api.TestStatus,
        skip_reason: t.Optional[str] = None,
        exc_info: t.Optional[ext_api.TestExcInfo] = None,
    ):
        log.debug(
            "Finishing ATR test retry %s for item %s, status: %s, skip_reason: %s, exc_info: %s",
            retry_number,
            item_id,
            status,
            skip_reason,
            exc_info,
        )
        core.dispatch(
            "test_visibility.atr.finish_retry",
            (
                ATRTestMixin.ATRRetryFinishArgs(
                    item_id, retry_number, status, skip_reason=skip_reason, exc_info=exc_info
                ),
            ),
        )

    @staticmethod
    @_catch_and_log_exceptions
    def atr_get_final_status(item_id: InternalTestId) -> ext_api.TestStatus:
        log.debug("Getting final ATR status for item %s", item_id)
        atr_final_status = core.dispatch_with_results(
            "test_visibility.atr.get_final_status", (item_id,)
        ).atr_final_status.value
        log.debug("Final ATR status for item %s: %s", item_id, atr_final_status)
        return atr_final_status
