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
    def parameters(self):
        return self['parameters']

    @parameters.setter
    def parameters(self, operation_object):
        self['parameters'] = operation_object

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


class ParameterObject(dict):
    def __init__(self, name, in_, description=None, required=False,
                 type_=None):
        super(ParameterObject, self).__init__()

        if in_ != 'body':
            if not type_:
                raise ValueError('type_ is required if in_ is not body')

        self['name'] = name
        self['in'] = in_
        if description:
            self['description'] = description
        if in_ == 'path' or required:
            self['required'] = True
        self['type'] = type_


class OperationObject(dict):
    def __init__(self, summary, tags=None):
        super(OperationObject, self).__init__()
        self.summary = summary
        self.responses = {}
        if tags:
            self.tags = tags

    @property
    def summary(self):
        return self['summary']

    @summary.setter
    def summary(self, new_summary):
        self['summary'] = new_summary

    @property
    def responses(self):
        return self['responses']

    @responses.setter
    def responses(self, new_responses):
        self['responses'] = new_responses

    @property
    def tags(self):
        return self['tags']

    @tags.setter
    def tags(self, new_tags):
        self['tags'] = new_tags


class ResponseObject(dict):
    def __init__(self, description):
        super(ResponseObject, self).__init__()
        self.description = description

    @property
    def description(self):
        return self['description']

    @description.setter
    def description(self, new_description):
        self['description'] = new_description


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


def _dict_representer(dumper, data):
    # Convert data to dict to remove the !!tag
    return dumper.represent_data(dict(data))

for _c in [SwaggerDoc, PathItem, OperationObject, ParameterObject,
           ResponseObject, ]:
    yaml.add_representer(_c, _dict_representer)


SWAGGER_DOC = SwaggerDoc()
