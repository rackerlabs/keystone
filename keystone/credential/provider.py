from oslo_config import cfg
from oslo_log import log

from keystone.common import manager
from keystone.common import dependency


CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.provider('credential_encryption_api')
class Manager(manager.Manager):

    driver_namespace = 'keystone.credential.provider'

    def __init__(self):
        super(Manager, self).__init__(CONF.credential.provider)
