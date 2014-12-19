# Copyright 2014 IBM Corp.
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

from keystone.common import dependency
from keystone.common import manager
from keystone import config

CONF = config.CONF


@dependency.provider('myfirstabac_api')
class Manager(manager.Manager):
    """Default pivot point for the MyFirstABAC backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        # NOTE(henry-nash): The driver for this manager is common to the
        # the driver for the assignment manager, since it is also responsible
        # for satisfying the assignment driver methods.
        super(Manager, self).__init__(CONF.assignment.driver)
