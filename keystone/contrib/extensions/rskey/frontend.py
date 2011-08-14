#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (c) 2010-2011 OpenStack, LLC.
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
RACKSPACE API KEY EXTENSION

This WSGI component
- detects calls with extensions in them.
- processes the necessary components
"""

import os
import sys
import json
import ast

from webob.exc import Request, Response

POSSIBLE_TOPDIR = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                   os.pardir,
                                   os.pardir,
                                   os.pardir,
                                   os.pardir))
if os.path.exists(os.path.join(POSSIBLE_TOPDIR, 'keystone', '__init__.py')):
    sys.path.insert(0, POSSIBLE_TOPDIR)

import keystone.utils as utils

EXTENSION_ALIAS = "RS-KEY"


class FrontEndFilter(object):
    """API Key Middleware that handles authentication with API Key"""

    def __init__(self, app, conf):
        """ Common initialization code """
        print "Starting the %s extension" % EXTENSION_ALIAS
        self.conf = conf
        self.app = app

    def __call__(self, env, start_response):
        """ Handle incoming request. Transform. And send downstream. """
        request = Request(env)
        if request.path == "/extensions":
            if env['KEYSTONE_API_VERSION'] == '2.0':

                request = Request(env)
                response = request.get_response(self.app)
                if response.status_int == 200:
                    if response.content_type == 'application/jsondd':
                        #handle json
                        #response.decode_content()
                        #body = json.loads(response.body)
                        #extensionsarray = body["extensions"]["values"]
                        #print __file__
                        #print os.path.pardir(__file__)

                        #print os.path.join(os.path.pardir(__file__), \
                        #                           "extension.json")
                        #thisextension = open(os.path.join(
                        #                            os.path.pardir(__file__),
                        #                           "extension.json")).read()
                        #thisextensionjson = json.loads(thisextension)
                        #extensionarray.append(thisextensionjson)
                        #newresp = Response(
                        #    content_type='application/json',
                        #    body=json.dumps(body))
                        #return resp
                        #return newresp(env, start_response)
                        pass
                    elif response.content_type == 'application/xmldd':
                        response.decode_content()

                        # Is this supposed to be a Response()?
                        return resp(env, start_response)

                # return the response
                return response(env, start_response)

                #response = self.app(env, self._sr_callback(start_response))
                #print response
                #print env
                #return response

        #default action, bypass
        return self.app(env, start_response)

    def _sr_callback(self, start_response):
        print 'sr'

        def callback(status, headers, exc_info=None):
            # Do something to modify the response status or headers
            print 'cb'

            # Call upstream start_response
            start_response(status, headers, exc_info)
        return callback


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def ext_filter(app):
        """Closure to return"""
        return FrontEndFilter(app, conf)
    return ext_filter
