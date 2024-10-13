import redis

from conf import REDIS_HOST, REDIS_PORT, REDIS_PASS, YC_CERT

cache = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    ssl=True,
    ssl_ca_certs=YC_CERT,
)
