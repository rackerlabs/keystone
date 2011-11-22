from webob import Response

from keystone import utils
from keystone.common import wsgi
from keystone.logic.extension_reader import ExtensionsReader


class ExtensionsController(wsgi.Controller):
    """Controller for extensions related methods"""

    def __init__(self, options, is_service_operation=None):
        super(ExtensionsController, self).__init__()
        self.options = options
        self.extension_reader = ExtensionsReader(options, is_service_operation)

    @utils.wrap_error
    def get_extensions_info(self, req):
        if utils.is_json_response(req):
            return Response(
                content_type='application/json',
                body=self.extension_reader.get_extensions_json())
        else:
            return Response(
                    content_type='application/xml',
                    body=self.extension_reader.get_extensions_xml())
