import os

import peewee_async

MYSQL_USER = 'app'
MYSQL_PASSWORD = 't3stpassw0rd'
MYSQL_DATABASE = 'test_db'
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)

if not MYSQL_USER or not MYSQL_PASSWORD:
    raise RuntimeError('mysql credentials not configured')

cdb = peewee_async.PooledMySQLDatabase(
    MYSQL_DATABASE,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    charset='utf8',
    max_connections=5
)