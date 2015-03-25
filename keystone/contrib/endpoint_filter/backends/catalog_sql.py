# Copyright 2013 OpenStack Foundation
#
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

from oslo_config import cfg
from oslo_log import log

from keystone.catalog.backends import sql
from keystone.catalog import core as catalog_core
from keystone.common import dependency
from keystone.i18n import _LW

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@dependency.requires('endpoint_filter_api')
class EndpointFilterCatalog(sql.Catalog):
    def get_v3_catalog(self, user_id, project_id,
                       metadata=None, unfiltered=False):

        LOG.warning(_LW('The EndpointFilterCatalog is deprecated.  '
                        'EndpointFiltering is now supported in the '
                        'default sql catalog driver.'))
        return super(EndpointFilterCatalog, self).get_v3_catalog(
            user_id,
            project_id,
            metadata=metadata,
            unfiltered=unfiltered)
