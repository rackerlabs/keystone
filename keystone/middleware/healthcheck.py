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

import os

import webob

from keystone.common import sql
from keystone.common import wsgi
from keystone.openstack.common import log
from oslo.config import cfg
import sqlalchemy

healthcheck_middleware_opts = [
    cfg.StrOpt('healthcheck_disable_file',
               default='/etc/keystone/disable.txt',
               help='A file to denote the service is disabled and/or '
                    'undergoing maintenance.')
]
cfg.CONF.register_opts(healthcheck_middleware_opts)

LOG = log.getLogger(__name__)


class HealthCheckMiddleware(wsgi.Middleware):
    """A middleware which provides a basic application health checking.

    Returns:
        '200 OK' on success
        '503 DISABLE BY FILE' when administratively disabled
        '503 DATABASE FAILED' when a database failure occurs
    """
    def __init__(self, application, **conf):
        self.application = application
        self.session = sql.get_session()

    def _check_db(self):
        """Check if the database is responding with a simple query.  Returns
        True while functioning.
        """
        try:
            s = sqlalchemy.select([sqlalchemy.func.now()])
            r = self.session.execute(s)
            r.fetchone()
            return True
        except Exception as e:
            LOG.exception(e)
            return False

    def _check_manual_disable(self):
        """Check for the presence of the `healthcheck_disable_file` flag.
        Returns True if exists on local disk.
        """
        return os.path.exists(cfg.CONF.healthcheck_disable_file)

    def _get(self, request):
        body, status = ('OK', 200)
        if self._check_manual_disable():
            body, status = ('DISABLED BY FILE', 503)
        elif not self._check_db():
            body, status = ('DATABASE FAILED', 503)

        return webob.Response(request=request, body=body,
                              content_type='text/plain', status=status)

    def process_request(self, request):
        if request.path == '/healthcheck':
            return self._get(request)
