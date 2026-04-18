import logging

from uvicorn.logging import AccessFormatter

logger = logging.getLogger('default')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(
    AccessFormatter('%(asctime)s - %(name)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s')
)
access_logger = logging.getLogger('uvicorn.access')
access_logger.handlers = [handler]
access_logger.propagate = False
