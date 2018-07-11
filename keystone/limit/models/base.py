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
import abc

import six
import stevedore

import keystone.conf
from keystone.i18n import _

CONF = keystone.conf.CONF


def load_driver(driver_name, *args):
    namespace = 'keystone.unified_limit.model'
    try:
        driver_manager = stevedore.DriverManager(namespace,
                                                 driver_name,
                                                 invoke_on_load=True,
                                                 invoke_args=args)
        return driver_manager.driver
    except stevedore.exception.NoMatches:
        msg = (_('Unable to find %(name)r driver in %(namespace)r.'))
        raise ImportError(msg % {'name': driver_name, 'namespace': namespace})


@six.add_metaclass(abc.ABCMeta)
class ModelBase(object):
    """Interface for a limit model driver."""

    NAME = None
    DESCRIPTION = None
    MAX_PROJECT_TREE_DEPTH = None

    def check_limit(self, project_id, resource_name, resource_limit,
                    service_id, region_id=None):
        """Check if a limit adhere to the properties of the enforcement model.

        :param project_id: The project identifier of the limit.
        :type project_id: str
        :param resource_name: The name of the resource for the limit.
        :type resource_name: str
        :param resource_limit: The number of resources associated to the limit.
        :type resource_limit: int
        :param service_id: The service identifier associated to the limit.
        :type service_id: str
        :param region_id: The region identifier associated to the limit.
        :type region_id: str

        :raises keystone.exception.InvalidLimit: If the properties of the limit
                                                 violate the characteristics of
                                                 the enforcement model.

        """
        raise NotImplementedError()
