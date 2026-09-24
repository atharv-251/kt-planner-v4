import sys
import os
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class ColoredFormatter(logging.Formatter):
    """Terminal colorized logging formatter."""
    GREY = "\033[90m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD_RED = "\033[1;91m"
    RESET = "\033[0m"

    LEVEL_COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        time_str = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        record_msg = record.getMessage()
        return f"{time_str} {color}[{record.levelname:<7}]{self.RESET} \033[36m[{record.name}]\033[0m: {record_msg}"

def setup_logging():
    """
    Configures console logging.
    Enables DEBUG level if '-v', '--verbose', or '--log-level debug' is in sys.argv,
    or if LOG_LEVEL=DEBUG in environment.
    """
    is_verbose = (
        "-v" in sys.argv
        or "--verbose" in sys.argv
        or any(arg.lower() in ("--log-level=debug", "debug") for arg in sys.argv)
        or os.getenv("LOG_LEVEL", "").upper() == "DEBUG"
    )

    log_level = logging.DEBUG if is_verbose else logging.INFO

    # Root handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(ColoredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers on reloads
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Configure application & uvicorn loggers
    for logger_name in ("kt_planner", "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        l = logging.getLogger(logger_name)
        l.setLevel(log_level)
        l.handlers = [handler]
        l.propagate = False

    logger = logging.getLogger("kt_planner")
    if is_verbose:
        logger.debug("VERBOSE/DEBUG logging mode active (triggered by -v flag or LOG_LEVEL=DEBUG).")
    else:
        logger.info("KT Planner logging initialized at INFO level. Pass '-v' to uvicorn to enable DEBUG.")

    return logger

class RealtimeRequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI Middleware providing real-time terminal logs for all HTTP requests,
    duration benchmarks, and error reporting.
    """
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("kt_planner.http")

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        method = request.method
        url_path = request.url.path
        query = request.url.query

        if query:
            self.logger.debug(f"--> {method} {url_path}?{query}")
        else:
            self.logger.debug(f"--> {method} {url_path}")

        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Suppress static assets logging to keep terminal clean unless in debug
            is_static = url_path.startswith("/assets/") or url_path.endswith((".ico", ".svg", ".png", ".jpg", ".js", ".css"))
            if not is_static or self.logger.isEnabledFor(logging.DEBUG):
                status = response.status_code
                if status >= 400:
                    self.logger.error(f"<-- {status} {method} {url_path} ({elapsed_ms:.1f}ms)")
                else:
                    self.logger.info(f"<-- {status} {method} {url_path} ({elapsed_ms:.1f}ms)")

            return response
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            self.logger.error(f"<!- FAIL {method} {url_path} ({elapsed_ms:.1f}ms): {exc}", exc_info=True)
            raise exc

