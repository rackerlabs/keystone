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

from oslo_config import cfg
import webob

from keystone.api.views import base

CONF = cfg.CONF


class View(base.BaseView):

    def member_url(self, obj):
        """The URL where the given object can be found.

        :param obj: The object to locate.
        :type obj: dict

        :rtype: str
        """
        # FIXME(jamielennox): we shouldn't assume v3 is mounted at /v3
        return '%s/v3/%s' % (self.host_url, self.member_path(obj).lstrip('/'))

    def create_response(self):
        """Create a basic v3 response.

        By overriding this a view can add new headers or data to all responses

        :rtype: :py:class:`webob.Response`
        """
        headerlist = [('Vary', 'X-Auth-Token')]
        return webob.Response(headerlist=headerlist)

    def show(self, obj, **kwargs):
        """Create a response that displays an object.

        :param obj: The object to show.
        :type obj: dict
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 200
        response.body = self._do_render('member', response, obj, **kwargs)
        return response

    def create(self, obj, **kwargs):
        """Create a response that displays an object that was just created.

        This is usually the same as the :py:func:`show` output but with the
        Created status code.

        :param obj: The object to show.
        :type obj: dict
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 201
        response.body = self._do_render('member', response, obj, **kwargs)
        return response

    def list(self, objs, truncated=False):
        """Create a response that displays a list of objects.

        :param objs: The objects to render.
        :type objs: list(dict)
        :param truncated: True if some elements were removed from the list.
        :type truncated: bool
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.status_code = 200
        response.body = self._do_render('list',
                                        response,
                                        objs,
                                        truncated=truncated)
        return response

    def delete(self, obj_id):
        """Render the response for a deleted object id.

        Note: this method receives an ID and not the full object as it has now
        been removed.

        :param obj_id: the ID of the recently removed object.
        :type obj_id: str
        :rtype: :py:class:`webob.Response`
        """
        response = self.create_response()
        response.body = b''
        response.status_code = 204
        return response
