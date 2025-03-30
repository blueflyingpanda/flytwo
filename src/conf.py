from os import environ

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = environ.get('BOT_TOKEN')

CLOUD_FUNC_URL = environ.get('CLOUD_FUNC_URL')

DB_USER = environ.get('DB_USER')
DB_PASS = environ.get('DB_PASS')
DB_HOST = environ.get('DB_HOST')
DB_PORT = environ.get('DB_PORT')
DB_NAME = environ.get('DB_NAME')

REDIS_PASS = environ.get('REDIS_PASS')
REDIS_HOST = environ.get('REDIS_HOST')
REDIS_PORT = environ.get('REDIS_PORT')
REDIS_TTL = environ.get('REDIS_TTL')

if REDIS_TTL is not None:
    REDIS_TTL = int(REDIS_TTL)

YC_CERT = environ.get('YC_CERT')

JWT_SECRET = environ.get('JWT_SECRET')
JWT_ACCESS_TOKEN_EXPIRE = environ.get('JWT_ACCESS_TOKEN_EXPIRE')

if JWT_ACCESS_TOKEN_EXPIRE is not None:
    JWT_ACCESS_TOKEN_EXPIRE = int(JWT_ACCESS_TOKEN_EXPIRE)

# JWT_REFRESH_TOKEN_EXPIRE = int(environ.get('JWT_REFRESH_TOKEN_EXPIRE'))

CORS_ORIGINS = environ.get('CORS_ORIGINS').split(',') if environ.get('CORS_ORIGINS') else ['*']
