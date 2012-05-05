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

import datetime
import logging

from keystone import config

CONF = config.CONF
config.register_int('expiration', group='security')
config.register_int('tolerance', group='security')


LOG = logging.getLogger(__name__)


class Action(object):

    def __init__(self, sec_api):
        self.sec_api = sec_api


class DummyAction(Action):

    def process_request(self, request):
        LOG.debug(request)

    def process_response(self, request, response):
        LOG.debug(response)
        return response


class Store_4xx_5xx_responses(Action):

    def process_response(self, request, response):
        if response.status_int >= 400 and response.status_int != 401:
            LOG.debug("Storing response with %s status code" %
                      response.status_int)
            _ = self.sec_api.store(request, response)
        return response


class Log_multiple_401(Action):
    def __init__(self, sec_api):
        self.expiration = CONF.security.expiration
        self.tolerance = CONF.security.tolerance
        super(Log_multiple_401, self).__init__(sec_api)

    def process_response(self, request, response):
        if response.status_int == 401:
            _ = self.sec_api.store(request, response)

            until = datetime.datetime.utcnow()
            since = until - datetime.timedelta(seconds=self.expiration)
            refs = self.sec_api.get((401,), since, until)

            if len(refs) >= self.tolerance:
                LOG.critical("%d 401 errors in %d seconds" %
                             (len(refs),self.expiration))
                for ref in refs:
                    self.sec_api.clean(ref)
        return response
