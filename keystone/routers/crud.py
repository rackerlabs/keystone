import routes

from keystone import config
from keystone.common import logging
from keystone.common import wsgi


LOG = logging.getLogger(__name__)


class Router(wsgi.ComposableRouter):
    def __init__(self, controller, collection_key, key):
        self.controller = controller
        self.key = key
        self.collection_key = collection_key

    def crud_routes(self, mapper, controller, collection_key, key):
        collection_path = '/%(collection_key)s' % {
            'collection_key': collection_key}
        entity_path = '/%(collection_key)s/{%(key)s_id}' % {
            'collection_key': collection_key,
            'key': key}

        mapper.connect(
            collection_path,
            controller=controller,
            action='create_%s' % key,
            conditions=dict(method=['POST']))
        mapper.connect(
            collection_path,
            controller=controller,
            action='list_%s' % collection_key,
            conditions=dict(method=['GET']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='get_%s' % key,
            conditions=dict(method=['GET']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='update_%s' % key,
            conditions=dict(method=['PATCH']))
        mapper.connect(
            entity_path,
            controller=controller,
            action='delete_%s' % key,
            conditions=dict(method=['DELETE']))

    def add_routes(self, mapper):
        self.crud_routes(mapper, self.controller, self.collection_key,
                         self.key)
