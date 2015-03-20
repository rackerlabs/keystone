# Copyright 2012 OpenStack Foundation
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

from oslo_serialization import jsonutils
import webob

from keystone.common import json_home


MEDIA_TYPE_JSON = 'application/vnd.openstack.identity-%s+json'

_VERSIONS = []

# NOTE(blk-u): latest_app will be set by keystone.service.loadapp(). It gets
# set to the application that was just loaded. In the case of keystone-all,
# loadapp() gets called twice, once for the public app and once for the admin
# app. In the case of httpd/keystone, loadapp() gets called once for the public
# app if this is the public instance or loadapp() gets called for the admin app
# if it's the admin instance.
# This is used to fetch the /v3 JSON Home response. The /v3 JSON Home response
# is the same whether it's the admin or public service so either admin or
# public works.
latest_app = None


def request_v3_json_home(new_prefix):
    req = webob.Request.blank(
        '/v3', headers={'Accept': 'application/json-home'})
    v3_json_home_str = req.get_response(latest_app).body
    v3_json_home = jsonutils.loads(v3_json_home_str)
    json_home.translate_urls(v3_json_home, new_prefix)

    return v3_json_home
