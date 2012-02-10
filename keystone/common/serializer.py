"""
Dict <--> XML de/serializer.

The identity API prefers attributes over elements, so we serialize that way
by convention, with a few hardcoded exceptions.

"""

from lxml import etree
import re


DOCTYPE = '<?xml version="1.0" encoding="UTF-8"?>'
XMLNS = 'http://docs.openstack.org/identity/api/v2.0'


def from_xml(xml):
    """Deserialize XML to a dictionary"""
    if xml is None:
        return None

    dom = etree.fromstring(xml.strip())
    return walk_element(dom)


def tag_name(tag):
    """Remove the namespace from the tagname.

    TODO(dolph): We might care about the namespace at some point.

    >>> tag_name('{xmlNamespace}tagName')
    'tagName'

    """
    m = re.search('[^}]+$', tag)
    return m.string[m.start():]


def walk_element(element):
    """Populates a dictionary by walking an element"""
    values = {}
    for k, v in element.attrib.iteritems():
        # boolean-looking attributes become booleans in JSON
        if k in ['enabled']:
            if v in ['true']:
                v = True
            elif v in ['false']:
                v = False

        values[k] = v

    text = None
    if element.text is not None:
        text = element.text.strip()

    # current spec does not have attributes on an element with text
    values = values or text or {}

    for child in map(walk_element, element):
        values = dict(values.items() + child.items())

    return {tag_name(element.tag): values}


def to_xml(d, xmlns=None):
    """Serialize a dictionary to XML"""
    if d is None:
        return None

    # FIXME(dolph): skipping links for now
    for key in d.keys():
        if '_links' in key:
            d.pop(key)

    assert len(d.keys()) == 1, \
            'Cannot encode more than one root element: %s' % d.keys()

    # name the root dom element
    name = d.keys()[0]

    # only the root dom element gets an xlmns
    root = etree.Element(name, xmlns=xmlns or XMLNS)

    populate_element(root, d[name])

    # TODO(dolph): you can get a doctype from lxml, using ElementTrees
    return '%s\n%s' % (DOCTYPE, etree.tostring(root, pretty_print=True))


def populate_element(element, d):
    """Populates an etree with the given dictionary"""
    if type(d) is list:
        for item in d:
            # xsd compliance: child elements are singular: <users> has <user>s
            child = etree.Element(element.tag[:-1])
            populate_element(child, item)
            element.append(child)
    else:
        # serialize a dictionary
        for k, v in d.iteritems():
            if type(v) is dict:
                child = etree.Element(k)
                populate_element(child, v)
                element.append(child)
            elif type(v) is list:
                # spec has a lot of inconsistency here!
                container = element

                if k == 'media-types':
                    # xsd compliance: <media-types> contains <media-type>s
                    # find an existing <media-types> element or make one
                    container = element.find('media-types')
                    if container is None:
                        container = etree.Element(k)
                        element.append(container)

                    name = k[:-1]
                elif k == 'serviceCatalog':
                    # xsd compliance: <serviceCatalog> contains <service>s
                    container = etree.Element(k)
                    element.append(container)

                    name = 'service'
                elif k == 'values':
                    # OS convention is to to contain lists in a 'values'
                    # element, so the list itself can have attributes, which
                    # is unnecessary in XML
                    name = element.tag[:-1]
                elif k[-1] == 's':
                    name = k[:-1]
                else:
                    name = k

                for item in v:
                    child = etree.Element(name)
                    populate_element(child, item)
                    container.append(child)
            elif type(v) is bool:
                # booleans are 'true' and 'false'
                element.set(k, unicode(v).lower())
            elif k in ['description'] and type(v) is str:
                # always becomes an element
                child = etree.Element(k)
                child.text = v
                element.append(child)
            else:
                # add attributes to the current element
                element.set(k, unicode(v))
