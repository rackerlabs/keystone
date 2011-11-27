
from keystone import utils
import os
import json
from lxml import etree

from keystone.contrib.extensions import CONFIG_EXTENSION_PROPERTY
from keystone.contrib.extensions import DEFAULT_EXTENSIONS
from keystone.logic.types.extension import Extensions
EXTENSIONS_PATH = 'contrib/extensions'


class ExtensionsReader(object):
    """Reader to read static extensions content"""

    def __init__(self, options, extension_prefix):
        self.options = options
        self.extension_prefix = extension_prefix
        self.root = None
        self.supported_extensions = None
        self.__init_extensions()

    def __init_extensions(self):
        self.extensions = Extensions(self.__get_json_extensions(),
            self.__get_xml_extensions())

    """ Initializes and returns all json static extension content."""
    def __get_json_extensions(self):
        body = self.__get_all_json_extensions()
        extensionsarray = body["extensions"]["values"]
        for supported_extension in self.__get_supported_extensions():
                thisextensionjson = self.__get_extension_json(
                    supported_extension)
                if thisextensionjson is not None:
                    extensionsarray.append(thisextensionjson)
        return json.dumps(body)

    """ Initializes and returns all xml static extension content."""
    def __get_xml_extensions(self):
        body = self.__get_all_xml_extensions()
        for supported_extension in self.__get_supported_extensions():
            thisextensionxml = self.__get_extension_xml(supported_extension)
            if thisextensionxml is not None:
                body.append(thisextensionxml)
        return etree.tostring(body)

    """ Returns application root.Has a local reference for reuse."""
    def __get_root(self):
        if self.root is None:
            self.root = utils.get_app_root()
            self.root = os.path.abspath(self.root) + os.sep
        return self.root

    """ Helper get file method."""
    def __get_file(self, resp_file):
        root = self.__get_root()
        filename = os.path.abspath(os.path.join(root, resp_file.strip('/\\')))
        return open(filename).read()

    """ Gets empty json extensions content to which specific
    extensions are added."""
    def __get_all_json_extensions(self):
        resp_file = "%s/%s.json" % (EXTENSIONS_PATH, 'extensions')
        allextensions = self.__get_file(resp_file)
        return json.loads(allextensions)

    """ Gets empty xml extensions content
    to which specific extensions are added."""
    def __get_all_xml_extensions(self):
        resp_file = "%s/%s.xml" % (EXTENSIONS_PATH, 'extensions')
        allextensions = self.__get_file(resp_file)
        return etree.fromstring(allextensions)

    """ Returns list of supported extensions."""
    def __get_supported_extensions(self):
        if self.supported_extensions is None:
            self.supported_extensions = self.options.get(
                CONFIG_EXTENSION_PROPERTY, DEFAULT_EXTENSIONS).split(',')
        return self.supported_extensions

    """Returns specific extension's json content."""
    def __get_extension_json(self, extension_name):
        thisextension = self.__get_extension_file(extension_name, 'json')
        return thisextension if not thisextension\
            else json.loads(thisextension.read())

    """Returns specific extension's xml content."""
    def __get_extension_xml(self, extension_name):
        thisextension = self.__get_extension_file(extension_name, 'xml')
        return thisextension if not thisextension\
            else etree.parse(thisextension).getroot()

    """Returns specific static extension file."""
    def __get_extension_file(self, extension_name, request_type):
        try:
            extension_dir = "%s/%s/%s" % (EXTENSIONS_PATH,\
                self.extension_prefix, extension_name)
            extension_dir = os.path.abspath(os.path.join(self.__get_root(),
                extension_dir.strip('/\\')))
            extension_file = open(os.path.join(extension_dir,
                "extension." + request_type))
            return extension_file
        except IOError:
            return None

    """Return Extensions result."""
    def get_extensions(self):
        return self.extensions
