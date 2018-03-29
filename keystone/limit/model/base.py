# Copyright 2018 Huawei
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

import stevedore

import keystone.conf
from keystone import exception
from keystone.i18n import _

CONF = keystone.conf.CONF


def load_driver(driver_name, *args):
    try:
        namespace = 'keystone.unified_limit.model'
        driver_manager = stevedore.DriverManager(namespace,
                                                 driver_name,
                                                 invoke_on_load=True,
                                                 invoke_args=args)
        return driver_manager.driver
    except stevedore.exception.NoMatches:
        msg = (_('Unable to find %(name)r driver in %(namespace)r.'))
        raise ImportError(msg % {'name': driver_name, 'namespace': namespace})


class ModelBase(object):
    """Interface for a limit model driver."""

    def check_limit(self, limit, project):
        """Check the new limit value whether satisfy the limit model.

        :param limit: The limit object need to be check.
        :type limit: A limit dict that contains "resource_limit",
            "resource_name", "project_id", "service_id" and optional
            "region_id", "description".
        :param project: The project of the limit.
        :type project: The project object.

        :raises keystone.exception.InvalidLimit: If the new limit doesn't
            satisfy the limit model.

        """
        raise exception.NotImplemented()  # pragma: no cover
