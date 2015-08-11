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

import datetime
import functools
import hashlib
import wsgiref.handlers

from oslo_utils import timeutils
import webob

from keystone.common import wsgi


def _etag_is_still_validate(headers):  # etag stuff may be overkill for a first round
    return False  # this no worky - it's pseudocode
    etag = headers.get('if-none-match')
    if not etag:
        return False

    if memcache.get('etag' + etag):
        return True  # the etag still exists

    return False


def naive_cache(expires_in=0, send_etag=False, public=True, private=False,
                must_revalidate=True, vary_token=False):
    def decorator(controller):
        @functools.wraps(controller)
        def decorated(self, context, *args, **kwargs):
            if send_etag and _etag_is_still_validate(context['headers']):
                return wsgi.render_response(status=(304, 'Not Modified'))

            now = timeutils.utcnow()

            result = controller(self, context, *args, **kwargs)
            if not isinstance(result, webob.Response):
                # TODO: doesn't support 201 Created yet
                result = wsgi.render_response(
                    body=result, method=context['environment']['REQUEST_METHOD'])

            # Support HTTP/1.0 clients
            expires = now + datetime.timedelta(seconds=expires_in)
            #result.headers['Expires'] = wsgiref.handlers.format_date_time(
            #    expires.timetuple())

            cachecontrol = []
            if public:
                cachecontrol.append('public')
            if private:
                cachecontrol.append('private')
            if must_revalidate:
                cachecontrol.append('must-revalidate')
            if expires_in:
                cachecontrol.append('max-age=%d' % expires_in)
            cachecontrol = ', '.join(cachecontrol)
            if cachecontrol:
                result.headers['Cache-Control'] = cachecontrol

            if send_etag:
                etag = hashlib.sha256(result.body)
                result.headers['Etag'] = etag
                #memcache.set('etag' + etag, expires_in, time=expires_in)

            return result

        return decorated
    return decorator
