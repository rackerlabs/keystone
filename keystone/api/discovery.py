#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import flask
from flask import request
from oslo_serialization import jsonutils
from six.moves import http_client

from keystone.common import json_home
from keystone.common import wsgi
import keystone.conf
from keystone import exception


CONF = keystone.conf.CONF
MEDIA_TYPE_JSON = 'application/vnd.openstack.identity-%s+json'
_VERSIONS = []

# NOTE(blk-u): latest_app will be set by keystone.version.service.loadapp(). It
# gets set to the application that was just loaded. loadapp() gets called once
# for the public app if this is the public instance or loadapp() gets called
# for the admin app if it's the admin instance. This is used to fetch the /v3
# JSON Home response. The /v3 JSON Home response is the same whether it's the
# admin or public service so either admin or public works.
latest_app = None


def register_version(version):
    _VERSIONS.append(version)


def _get_versions_list(identity_url):
    versions = {}
    if 'v3' in _VERSIONS:
        versions['v3'] = {
            'id': 'v3.10',
            'status': 'stable',
            'updated': '2018-02-28T00:00:00Z',
            'links': [
                {
                    'rel': 'self',
                    'href': identity_url,
                }
            ],
            'media-types': [
                {
                    'base': 'application/json',
                    'type': MEDIA_TYPE_JSON % 'v3'
                }
            ]
        }

    return versions


class MimeTypes(object):
    JSON = 'application/json'
    JSON_HOME = 'application/json-home'


def v3_json_home_content():
    if 'v3' not in _VERSIONS:
        # No V3 Support, ro return an empty JSON Home document.
        return {'resources': {}}
    return json_home.JsonHomeResources.resources()


_DISCOVERY_BLUEPRINT = flask.Blueprint('Discovery', __name__)


class DiscoveryAPI(object):
    # NOTE(morgan): The Discovery Bits are so special they cannot conform to
    # Flask-RESTful-isms. We are using straight flask Blueprint(s) here so that
    # we have a lot more control over what the heck is going on.

    @property
    def _is_json_home_request(self):
        req_mime_type = request.accept_mimetypes.best_match(
            [MimeTypes.JSON, MimeTypes.JSON_HOME])
        return req_mime_type == MimeTypes.JSON_HOME

    @_DISCOVERY_BLUEPRINT.route('/')
    def get_versions(self):
        if self._is_json_home_request:
            # RENDER JSON-Home form, we have a clever client who will
            # understand the JSON-Home document.
            v3_json_home = json_home.translate_urls(
                v3_json_home_content(), '/v3')
            return flask.Response(
                jsonutils.dumps(v3_json_home), mimetype=MimeTypes.JSON_HOME)
        else:
            # NOTE(morgan): wsgi.Application.base_url will eventually need to
            # be moved to a better "common" location. For now, we'll just lean
            # on it for the sake of leaning on common code where possible.
            identity_url = '/v3/%s/' % wsgi.Application.base_url(
                context={'environment': request.environ})
            return flask.Response(
                jsonutils.dumps(_get_versions_list(identity_url)),
                status_code=http_client.MULTIPLE_CHOICES,
                status=http_client.responses[http_client.MULTIPLE_CHOICES])

    @_DISCOVERY_BLUEPRINT.route('/v3')
    def get_version_v3(self):
        if 'v3' not in _VERSIONS:
            raise exception.VersionNotFound(version='v3')

        if self._is_json_home_request:
            # RENDER JSON-Home form, we have a clever client who will
            # understand the JSON-Home document.
            data = v3_json_home_content()
            return flask.Response(
                jsonutils.dumps(data), mimetype=MimeTypes.JSON_HOME)
        else:
            # NOTE(morgan): wsgi.Application.base_url will eventually need to
            # be moved to a better "common" location. For now, we'll just lean
            # on it for the sake of leaning on common code where possible.
            identity_url = '/v3/%s/' % wsgi.Application.base_url(
                context={'environment': request.environ})
            versions = _get_versions_list(identity_url)
            return flask.Response(
                jsonutils.dumps({'version': versions['v3']}),
                mimetype=MimeTypes.JSON)

    @classmethod
    def instantiate_and_register_to_app(cls, flask_app):
        flask_app.register(cls())


APIs = (DiscoveryAPI,)
