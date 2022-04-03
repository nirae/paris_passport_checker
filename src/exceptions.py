"""Slot checker exceptions"""

import logging as log
import traceback


def passport_checker_exception(exception, msg=None):
    """Exception handler

    All caught exceptions should call this function.
    Captures traceback unless debug logs are activated.
    Raises generic PassportCheckerException before program terminates.

    Args:
        - exception: exception initially caught
        - msg: optional custom error log
    """

    if msg is not None:
        exc = exception.__name__ if hasattr(exception, __name__) else exception
        log.error(msg)
        log.error("Error originating from %s", exc)
    debug = log.getLogger().getEffectiveLevel() == log.DEBUG
    if not debug:
        log.warning("Traceback may be suppressed. Activate debug logs to see.")
    else:
        traceback.print_exc()
    raise PassportCheckerException(exception)


class PassportCheckerException(Exception):
    """Generic Slot Checker exception"""

    def __init__(self, origin):
        super().__init__()
        self.error_code = 1
