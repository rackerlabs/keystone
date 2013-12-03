# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo.config import cfg
import six

from keystone.openstack.common import log

CONF = cfg.CONF

FILE_OPTIONS = {
    None: (None, [
        cfg.StrOpt('bind_ip',
                   default='0.0.0.0',
                   help='IP for the server to bind to'),
        cfg.IntOpt('port',
                   default=9109,
                   help='The port for the server'),
    ]),
    'kds': ('Key Distribution Service', [
        cfg.StrOpt('master_key_file',
                   default='/etc/keystone/kds.mkey',
                   help='The location of the KDS master key. MUST be private. '
                        'If missing or unavailable one will be created.'),
        cfg.StrOpt('enctype',
                   default='AES',
                   help='Encryption Algorithm used to encrypt service keys '
                        'for storing in the database.'),
        cfg.StrOpt('hashtype',
                   default='SHA256',
                   help='Hashing Algorithm used when generating signatures '
                        'for integrity when storing keys to the database'),
        cfg.IntOpt('ticket_lifetime',
                   default=3600,
                   help='Length of ticket validity (in seconds)'),
    ]),
}


def configure(conf=None):
    if conf is None:
        conf = CONF

    for group, (title, options) in six.iteritems(FILE_OPTIONS):
        if title:
            conf.register_group(cfg.OptGroup(name=group, title=title))
        conf.register_opts(options, group=group)


def parse_args(args, default_config_files=None):
    CONF(args=args[1:],
         project='kds',
         default_config_files=default_config_files)


def prepare_service(argv=[]):
    cfg.set_defaults(log.log_opts,
                     default_log_levels=['sqlalchemy=WARN',
                                         'eventlet.wsgi.server=WARN'
                                         ])
    parse_args(argv)
    log.setup('kds')


configure()
