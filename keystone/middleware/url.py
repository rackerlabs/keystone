#!/usr/bin/env python
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


"""
URL normalizer Middleware.

This module can be installed as a filter in front of your service to
normalize URL. Right now it just provides trailing slash normalization.

"""


class NormalizingFilter(object):
    """Middleware filter to handle URL and Accept header normalization."""

    def __init__(self, app, conf):
        # app is the next app in WSGI chain - eventually the OpenStack service
        self.app = app
        self.conf = conf

    def __call__(self, env, start_response):
        env['PATH_INFO'] = normalize_trailing_slash(env['PATH_INFO'])
        return self.app(env, start_response)


def normalize_trailing_slash(path_info):
    """Removes a trailing slash from the given path, if any."""
    if len(path_info) > 1 and path_info[-1] == '/':
        return path_info[:-1]
    else:
        return path_info


def filter_factory(global_conf, **local_conf):
    """Returns a WSGI filter app for use with paste.deploy."""
    conf = global_conf.copy()
    conf.update(local_conf)

    def ext_filter(app):
        return NormalizingFilter(app, conf)
    return ext_filter
