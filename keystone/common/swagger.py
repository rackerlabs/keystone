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

import yaml


class PathItem(dict):
    @property
    def get(self):
        return self['get']

    @get.setter
    def get(self, operation_object):
        self['get'] = operation_object

    @property
    def head(self):
        return self['head']

    @head.setter
    def head(self, operation_object):
        self['head'] = operation_object

    @property
    def put(self):
        return self['put']

    @put.setter
    def put(self, operation_object):
        self['put'] = operation_object

    @property
    def post(self):
        return self['post']

    @post.setter
    def post(self, operation_object):
        self['post'] = operation_object

    @property
    def patch(self):
        return self['patch']

    @patch.setter
    def patch(self, operation_object):
        self['patch'] = operation_object

    @property
    def delete(self):
        return self['delete']

    @delete.setter
    def delete(self, operation_object):
        self['delete'] = operation_object


class SwaggerDoc(dict):
    def __init__(self):
        super(SwaggerDoc, self).__init__()
        self.update({
            'swagger': '2.0',
            'info': {
                'title': 'OpenStack Identity API V3',
                'version': '3.6',
            },
            'paths': {}
        })

    def register_path(self, path, pathitem):
        self['paths'][path] = pathitem


def dict_representer(dumper, data):
    # Convert data to dict to remove the !!tag
    return dumper.represent_data(dict(data))

yaml.add_representer(SwaggerDoc, dict_representer)
yaml.add_representer(PathItem, dict_representer)

SWAGGER_DOC = SwaggerDoc()
