
from keystone import utils
import os
import json
from lxml import etree

from keystone.contrib.extensions import CONFIG_EXTENSION_PROPERTY
from keystone.contrib.extensions import DEFAULT_EXTENSIONS
from keystone.contrib.extensions.admin import EXTENSION_ADMIN_PREFIX
from keystone.contrib.extensions.service import EXTENSION_SERVICE_PREFIX
EXTENSIONS_PATH = 'contrib/extensions'


class ExtensionsReader(object):
    """Reader to read static extensions content"""

    def __init__(self, options, is_service_operation=None):
        self.options = options
        if is_service_operation:
            self.extension_prefix = EXTENSION_SERVICE_PREFIX
        else:
            self.extension_prefix = EXTENSION_ADMIN_PREFIX
        self.json_body = None
        self.xml_body = None
        self.root = None
        self.supported_extensions = None
        self.__init_extensions()

    def __init_extensions(self):
        self.__init_json_extensions()
        self.__init_xml_extensions()

    def __init_json_extensions(self):
        body = self.__get_all_json_extensions()
        extensionsarray = body["extensions"]["values"]
        for supported_extension in self.__get_supported_extensions():
                thisextensionjson = self.__get_extension_json(
                    supported_extension)
                if thisextensionjson is not None:
                    extensionsarray.append(thisextensionjson)
        self.json_body = json.dumps(body)

    def __init_xml_extensions(self):
        body = self.__get_all_xml_extensions()
        for supported_extension in self.__get_supported_extensions():
            thisextensionxml = self.__get_extension_xml(supported_extension)
            if thisextensionxml is not None:
                body.append(thisextensionxml)
        self.xml_body = etree.tostring(body)

    def __get_root(self):
        if self.root is None:
            self.root = utils.get_app_root()
            self.root = os.path.abspath(self.root) + os.sep
        return self.root

    def __get_file(self, resp_file):
        root = self.__get_root()
        filename = os.path.abspath(os.path.join(root, resp_file.strip('/\\')))
        return open(filename).read()

    def __get_all_json_extensions(self):
        resp_file = "%s/%s.json" % (EXTENSIONS_PATH, 'extensions')
        allextensions = self.__get_file(resp_file)
        return json.loads(allextensions)

    def __get_all_xml_extensions(self):
        resp_file = "%s/%s.xml" % (EXTENSIONS_PATH, 'extensions')
        allextensions = self.__get_file(resp_file)
        return etree.fromstring(allextensions)

    def __get_supported_extensions(self):
        if self.supported_extensions is None:
            self.supported_extensions = self.options.get(
                CONFIG_EXTENSION_PROPERTY, DEFAULT_EXTENSIONS).split(',')
        return self.supported_extensions

    def __get_extension_json(self, extension_name):
        try:
            thisextension = self.__get_extension_file(extension_name, 'json')
            thisextensionjson = json.loads(thisextension.read())
            return thisextensionjson
        except IOError:
            return None

    def __get_extension_xml(self, extension_name):
        try:
            thisextension = self.__get_extension_file(extension_name, 'xml')
            extension_xml = etree.parse(thisextension).getroot()
            return extension_xml
        except IOError:
            return None

    def __get_extension_file(self, extension_name, request_type):
        extension_dir = "%s/%s/%s" % (EXTENSIONS_PATH,\
            self.extension_prefix, extension_name)
        extension_dir = os.path.abspath(os.path.join(self.__get_root(),
            extension_dir.strip('/\\')))
        extension_file = open(os.path.join(extension_dir,
            "extension." + request_type))
        return extension_file

    def get_extensions_xml(self):
        return self.xml_body

    def get_extensions_json(self):
        return self.json_body
