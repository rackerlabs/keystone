from keystone.common import config

import dogpile.cache


CONF = config.CONF

# FIXME(dolph): untested whether CONF is referenced too early here
REGION = dogpile.cache.make_region().configure(
    'dogpile.cache.redis',
    expiration_time=CONF.cache.duration,
    arguments={
        'host': CONF.cache.host,
        'port': CONF.cache.port,
        'db': 0,
        'distributed_lock': True,
    }
)

on_arguments = REGION.cache_on_arguments
