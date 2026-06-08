"""Simple color logging handler — no external dependencies."""

import logging
import sys

_USE_COLOR = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

_LEVEL_COLORS = {
    logging.DEBUG:    "\033[2m",
    logging.INFO:     "\033[0m",
    logging.WARNING:  "\033[33m",
    logging.ERROR:    "\033[31m",
    logging.CRITICAL: "\033[31;1m",
}
_RESET = "\033[0m"


class ColorHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(stream=sys.stdout)
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            if _USE_COLOR:
                color = _LEVEL_COLORS.get(record.levelno, "")
                line = (
                    f"{color}{record.levelname}: {msg}{_RESET}"
                    if record.levelno >= logging.WARNING
                    else f"{color}{msg}{_RESET}"
                )
            else:
                line = (
                    f"{record.levelname}: {msg}"
                    if record.levelno >= logging.WARNING
                    else msg
                )
            stream = sys.stderr if record.levelno >= logging.WARNING else sys.stdout
            print(line, file=stream)
        except Exception:
            self.handleError(record)
