from helper.config import LOG_LEVEL
import logging
import sys

# or doesn't have a valid log level value
default_log_level = logging.ERROR

# Map log level names to their corresponding logging constants
log_level_mapping = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Determine the log level based on the environment variable
log_level = log_level_mapping.get(LOG_LEVEL, default_log_level)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s [%(filename)s:%(lineno)s - %(funcName)s ] - %(message)s",
    level=log_level,
    stream=sys.stdout,  # directing logs to the standard output
)
