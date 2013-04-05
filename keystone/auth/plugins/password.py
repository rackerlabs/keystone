import logging

LOG = logging.getLogger(__name__)
LOG.warn('DEPRECATED: moved to keystone.auth.password')

from keystone.auth.password import *
