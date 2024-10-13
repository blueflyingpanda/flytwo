import redis

from conf import REDIS_HOST, REDIS_PORT, REDIS_PASS, YC_CERT

r = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASS,
    ssl=True,
    ssl_ca_certs=YC_CERT,
)

if __name__ == '__main__':
    # r.set("foo", "bar")
    print(r.get("foo"))
