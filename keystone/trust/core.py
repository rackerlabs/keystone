# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack LLC
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

"""Main entry point into the Identity service."""

from keystone.common import dependency
from keystone.common import logging
from keystone.common import manager
from keystone import config
from keystone import exception

from keystone.common import cache


CONF = config.CONF

LOG = logging.getLogger(__name__)


@dependency.provider('trust_api')
class Manager(manager.Manager):
    """Default pivot point for the Trust backend.

    See :mod:`keystone.common.manager.Manager` for more details on how this
    dynamically calls the backend.

    """

    def __init__(self):
        super(Manager, self).__init__(CONF.trust.driver)

    @cache.on_arguments()
    def get_trust(self, trust_id):
        return self.driver.get_trust(trust_id)

    @cache.on_arguments()
    def list_trusts(self):
        return self.driver.list_trusts()

    # FIXME(morganfainberg): enable caching of this trust calls. Requires
    # logic to properly invalidate cache.
    #@cache.on_arguments()
    #def list_trusts_for_trustee(self, trustee):
    #    return self.driver.list_trusts_for_trustee(trustee)

    # FIXME(morganfainberg): enable caching of this trust calls. Requires
    # logic to properly invalidate cache.
    #@cache.on_arguments()
    #def list_trusts_for_trustor(self, trustor):
    #    return self.driver.list_trusts_for_trustor(trustor)

    def create_trust(self, trust_id, trust, roles):
        ret = self.driver.create_trust(trust_id, trust, roles)
        self.list_trusts.invalidate()
        return ret

    def delete_trust(self, trust_id):
        self.driver.delete_trust(trust_id)
        self.list_trusts.invalidate()
        self.get_trust.invalidate(trust_id)


class Driver(object):
    def create_trust(self, trust_id, trust, roles):
        """Create a new trust.

        :returns: a new trust
        """
        raise exception.NotImplemented()

    def get_trust(self, trust_id):
        raise exception.NotImplemented()

    def list_trusts(self):
        raise exception.NotImplemented()

    def list_trusts_for_trustee(self, trustee):
        raise exception.NotImplemented()

    def list_trusts_for_trustor(self, trustor):
        raise exception.NotImplemented()

    def delete_trust(self, trust_id):
        raise exception.NotImplemented()
