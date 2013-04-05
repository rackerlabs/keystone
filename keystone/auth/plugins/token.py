import logging

LOG = logging.getLogger(__name__)
LOG.warn('DEPRECATED: moved to keystone.auth.token')

from keystone.auth.token import *
