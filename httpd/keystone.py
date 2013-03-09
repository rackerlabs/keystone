import os
import sys

from paste import deploy

from keystone import config
from keystone.common import logging

LOG = logging.getLogger(__name__)
CONF = config.CONF
CONF(project='keystone')

if CONF.config_file:
    conf = CONF.config_file[0]

name = os.path.basename(__file__)

if CONF.debug:
    CONF.log_opt_values(logging.getLogger(CONF.prog), logging.DEBUG)

if CONF.paste_deploy.config_file:
    paste_config = CONF.paste_deploy.config_file
    paste_config_value = paste_config
    if not os.path.isabs(paste_config):
        paste_config = CONF.find_file(paste_config)
elif CONF.config_file:
    paste_config = CONF.config_file[0]
    paste_config_value = paste_config
else:
    paste_config = CONF.find_file('keystone.conf')
    paste_config_value = 'keystone.conf'
if not paste_config or not os.path.exists(paste_config):
    print >> sys.stderr, "The %s file could not be found." % paste_config_value
else:
    application = deploy.loadapp('config:%s' % paste_config, name=name)
