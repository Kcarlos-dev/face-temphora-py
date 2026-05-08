import logging
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    "system.log",
    when="D",
    interval=3,
    backupCount=10
)

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    format="%(asctime)s - %(levelname)s - %(message)s"
)
