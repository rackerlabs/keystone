"""
Dict to XML serializer.

The identity API prefers attributes over elements, so we serialize that way
by convention, and TODO(dolph): configure exceptions.

"""

from lxml import etree


DOCTYPE = '<?xml version="1.0" encoding="UTF-8"?>'
XMLNS = 'http://docs.openstack.org/identity/api/v2.0'


def to_xml(d, xmlns = None):
    """Serialize a dictionary to XML"""
    assert len(d.keys()) == 1, 'Cannot encode more than one root element'

    # name the root dom element
    name = d.keys()[0]

    # only the root dom element gets an xlmns, TODO(dolph): ... I think?
    root = etree.Element(name, xmlns=xmlns or XMLNS)

    populate_element(root, d[name])

    # TODO(dolph): we don't actually need to pretty print for real clients
    # TODO(dolph): i think there's a way to get a doctype from lxml?
    return '%s\n%s' % (DOCTYPE, etree.tostring(root, pretty_print=True))


def populate_element(element, d):
    """Populates an etree with the given dictionary"""
    for k, v in d.iteritems():
        if type(v) is dict:
            # serialize the child dictionary
            child = etree.Element(k)
            populate_element(child, v)
            element.append(child)
        elif type(v) is list:
            # serialize the child list
            # TODO(dolph): this is where the spec has a LOT of inconsistency, but this covers 80% of it
            if k[-1] == 's':
                name = k[:-1]
            else:
                name = k

            for item in v:
                child = etree.Element(name)
                populate_element(child, item)
                element.append(child)
        elif type(v) is bool:
            # booleans are are 'true' and 'false'
            element.set(k, unicode(v).lower())
        elif k in ['description'] and type(v) is str:
            # certains attributes should always become elements
            child = etree.Element(k)
            child.text = v
            element.append(child)
        else:
            # add attributes to the current element
            element.set(k, unicode(v))
