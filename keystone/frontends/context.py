#!/usr/bin/env python
#
# Copyright (c) 2011 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Auth Context Module

This WSGI component extracts auth information from the request and stores
it in the request's 'environ' dict. This eliminates the need for other parts
of the code to repeatedly determine this info from the supplied credentials
or token.
"""
import copy
import datetime
import logging
import uuid
from webob.exc import Request
from keystone import utils
from keystone.common import wsgi

logger = logging.getLogger(__name__)  # pylint: disable=C0103


def one_day_hence():
    return datetime.datetime.now() + datetime.timedelta(days=1)


class RequestContext(object):
    """Authentication context and request information.

    Represents the auth information for the current request.
    """
    def __init__(self, token_id, user_id, tenant_id, expires=None):
        self.token_id = token_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.expires = expires or one_day_hence()
        self.has_admin_role = False
        self.has_service_admin_role = False
        self.identity_service = None
        self._auth_data = None


class ContextFilter(object):
    """Extracts auth information from the request and stores it in a
    RequestContext object. A reference to this object is then stored in:
    request.environ['context'].
    """
    def __init__(self, app, conf):
        """ Common initialization code """
        msg = _("Starting the ContextFilter middleware.")
        logger.info(msg)
        self.conf = conf
        self.app = app

    def __call__(self, env, start_response):
        """ Handle incoming request. Transform. And send downstream. """
        logger.debug("Entering Context.__call__")
        request = Request(env)
        reqenv = request.environ
        token = reqenv.get("HTTP_X_AUTH_TOKEN")
        context = RequestContext(token, None, None)
        reqenv["context"] = context
        return self.app(env, start_response)


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def context_filter(wsgiapp):
        """Closure to return"""
        return ContextFilter(wsgiapp, conf)
    return context_filter
