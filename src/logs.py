import logging

from uvicorn.logging import AccessFormatter

logger = logging.getLogger('default')
logger.setLevel(logging.DEBUG)
logger.propagate = False

_default_handler = logging.StreamHandler()
_default_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(_default_handler)

_access_handler = logging.StreamHandler()
_access_handler.setFormatter(
    AccessFormatter('%(asctime)s - %(name)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s')
)
access_logger = logging.getLogger('uvicorn.access')
access_logger.addHandler(_access_handler)
access_logger.propagate = False
