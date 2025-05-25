"""
Logging utility for the ITF Tennis Scraper application.

Provides a centralized way to configure and obtain loggers.
"""
import asyncio
import logging
import logging.handlers
import sys
import time  # For PerformanceLogger and TimedContext
from functools import wraps  # For TimedContext decorator
from pathlib import Path
from typing import Any, List, Optional  # Added Any for TimedContext

# --- Global Log Settings (Defaults, can be overridden by Config) ---
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "tennis_scraper.log"
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(levelname)-8s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_LOG_FILE_SIZE_MB = 10
LOG_BACKUP_COUNT = 5

_logging_configured = False


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    log_file: Optional[str] = DEFAULT_LOG_FILE,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    max_bytes: int = MAX_LOG_FILE_SIZE_MB * 1024 * 1024,
    backup_count: int = LOG_BACKUP_COUNT,
    log_to_console: bool = True,
):
    """
    Configures root logging with a file handler and optional console handler.
    This function should ideally be called once at application startup.
    """
    global _logging_configured

    log_level_upper = level.upper()
    numeric_level = getattr(logging, log_level_upper, logging.INFO)
    formatter = logging.Formatter(log_format, date_format)
    root_logger = logging.getLogger()

    # Prevent re-configuring if already done by another part of the app that imports this.
    # A more robust way might involve checking root_logger.hasHandlers(),
    # but this flag is simpler for now.
    if (
        _logging_configured
        and root_logger.level == numeric_level
        and len(root_logger.handlers) > 0
    ):
        # If level is the same and handlers exist, assume it's configured.
        # This might need adjustment if config changes log level at runtime.
        logging.getLogger(__name__).debug(
            "Logging setup skipped, seems already configured."
        )
        return

    root_logger.setLevel(numeric_level)

    for handler in root_logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        root_logger.removeHandler(handler)

    if log_file:
        log_file_path = Path(log_file)
        try:
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            # file_handler.setLevel(numeric_level) # Level on root is usually enough
            root_logger.addHandler(file_handler)
            # Use print here as logging might not be fully set up for the logger itself yet
            print(f"INFO: Logging to file: {log_file_path} at level {log_level_upper}")
        except Exception as e:
            print(
                f"ERROR: Failed to set up file logging for {log_file_path}: {e}",
                file=sys.stderr,
            )
            log_to_console = True

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        # console_handler.setLevel(numeric_level) # Level on root is usually enough
        root_logger.addHandler(console_handler)
        # Avoid double printing if file logging also failed
        if not log_file or (
            log_file
            and not any(
                isinstance(h, logging.FileHandler) for h in root_logger.handlers
            )
        ):
            print(f"INFO: Logging to console at level {log_level_upper}")

    noisy_libraries = {
        "selenium.webdriver.remote.remote_connection": logging.WARNING,
        "selenium.webdriver.common.service": logging.WARNING,
        "urllib3.connectionpool": logging.WARNING,
        "aiohttp": logging.WARNING,
        "asyncio": logging.INFO,  # Debug is often too verbose for asyncio
        "websockets.client": logging.INFO,
        "websockets.server": logging.INFO,
    }
    for lib_name, lib_level in noisy_libraries.items():
        logging.getLogger(lib_name).setLevel(lib_level)

    _logging_configured = True
    # Use a logger obtained AFTER basicConfig might have run.
    logging.getLogger(__name__).info(
        "-" * 20 + " Logging System Initialized " + "-" * 20
    )
    logging.getLogger(__name__).info(
        f"Python Version: {sys.version.split()[0]}, Platform: {sys.platform}"
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Returns a logger instance with the specified name.
    If name is None, returns the root logger.
    Ensures that basic logging is configured if it hasn't been already.
    """
    if not _logging_configured:
        # This is a fallback. Ideally, setup_logging is called explicitly once at app start.
        print(
            f"WARNING: Logging was not explicitly configured. Falling back to default setup for logger '{name}'.",
            file=sys.stderr,
        )
        setup_logging()
    return logging.getLogger(name)


def get_recent_logs(
    num_lines: int = 100, log_file_path: Optional[str] = None
) -> List[str]:
    """
    Retrieves the last N lines from the log file.
    Uses the default log file if none is provided.
    """
    if log_file_path is None:
        # Try to get the log file path from currently configured handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler) or isinstance(
                handler, logging.FileHandler
            ):
                log_file_path = handler.baseFilename
                break
        if log_file_path is None:  # Fallback to default if no file handler found
            log_file_path = DEFAULT_LOG_FILE

    actual_log_file = Path(log_file_path)
    if not actual_log_file.exists():
        return [f"Log file not found: {actual_log_file}"]

    try:
        with open(actual_log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-num_lines:]]
    except Exception as e:
        return [f"Error reading log file {actual_log_file}: {e}"]


def get_log_file_path() -> Optional[str]:
    """Returns the absolute path to the currently configured log file, if any."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler) or isinstance(
            handler, logging.FileHandler
        ):
            return handler.baseFilename
    return None


class PerformanceLogger:
    """Simple utility to log execution times of code blocks."""

    def __init__(self):
        self.logger = get_logger(f"{__name__}.Performance")
        self.timings = {}
        self._start_times = {}

    def start(self, block_name: str):
        """Start timing a block."""
        self._start_times[block_name] = time.perf_counter()

    def stop(self, block_name: str, log_message: Optional[str] = None) -> float:
        """Stop timing a block and log the duration."""
        if block_name not in self._start_times:
            self.logger.warning(f"Timer for '{block_name}' was not started.")
            return -1.0

        duration = time.perf_counter() - self._start_times.pop(block_name)
        self.timings[block_name] = duration

        if log_message:
            self.logger.info(f"{log_message} - Duration: {duration:.4f} seconds")
        else:
            self.logger.info(f"Block '{block_name}' executed in {duration:.4f} seconds")
        return duration

    def time_block(self, block_name: str):
        """Context manager for timing a block of code."""
        return TimedContext(self, block_name)

    def get_last_duration(self, block_name: str) -> Optional[float]:
        return self.timings.get(block_name)


class TimedContext:
    """Context manager for use with PerformanceLogger."""

    def __init__(self, perf_logger: PerformanceLogger, block_name: str):
        self.perf_logger = perf_logger
        self.block_name = block_name

    def __enter__(self):
        self.perf_logger.start(self.block_name)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        self.perf_logger.stop(self.block_name)
        # Do not suppress exceptions: return False or None
        return False


def timed(block_name_or_func: Optional[str] = None):
    """
    Decorator to time a function's execution.
    Can be used as @timed or @timed("custom_block_name").
    """
    perf_logger_instance = PerformanceLogger()

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            block_name = (
                block_name_or_func
                if isinstance(block_name_or_func, str)
                else func.__name__
            )
            perf_logger_instance.start(block_name)
            try:
                return await func(*args, **kwargs)
            finally:
                perf_logger_instance.stop(block_name)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            block_name = (
                block_name_or_func
                if isinstance(block_name_or_func, str)
                else func.__name__
            )
            perf_logger_instance.start(block_name)
            try:
                return func(*args, **kwargs)
            finally:
                perf_logger_instance.stop(block_name)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    if callable(block_name_or_func):  # Used as @timed
        return decorator(block_name_or_func)
    else:  # Used as @timed("name")
        return decorator
