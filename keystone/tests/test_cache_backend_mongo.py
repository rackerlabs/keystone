import binascii
import uuid
from bson.binary import Binary

from keystone.openstack.common import timeutils
from keystone import exception
from keystone import tests
from keystone.common import cache

from dogpile.cache import make_region
from dogpile.cache import api

import mongomock


ks_cache = {
    "cache": [
        {
            "value": {
                "_type": "dogpile.cache.api.CachedValue",
                "_type_value": [
                    [
                        {
                            "serviceType": "identity",
                            "allVersionsUrl": "https://dummyUrl",
                            "dateLastModified":
                            "{ISO8601_DATE}2014-02-08T18:39:13.237000Z",
                            "serviceName": "Identity",
                            "enabled": "{BOOLEAN}True",
                        }
                    ],
                    {
                        "v": 1,
                        "ct": 1391808977.693244
                    }
                ]
            },
            "key": "get_service_by_name",
            "doc_date": "{ISO8601_DATE}2014-02-08T18:39:13.237000Z"
        },
        {
            "value": {
                "_type": "dogpile.cache.api.CachedValue",
                "_type_value": [
                    "dummyValue",
                    {
                        "v": 1,
                        "ct": 1391828529.061648
                    }
                ]
            },
            "key": "a844cf5b941f45b7aef6630754862cd7",
            "doc_date": "{ISO8601_DATE}2014-02-08T03:02:09.061Z"
        }
    ]
           }


def from_dict(elem):
    new_elem = {}
    for k, v in elem.iteritems():
        if isinstance(v, basestring):
            if v.startswith('{BINARY}'):
                v = Binary(binascii.a2b_hex(v[8:]))
            elif v.startswith('{ISO8601_DATE}'):
                v = timeutils.parse_isotime(v[14:])
                v = timeutils.normalize_time(v)
            elif v.startswith('{BOOLEAN}'):
                v = v[9:].lower() == 'true'
        new_elem[k] = v
    return new_elem


class Cursor(mongomock.collection.Cursor):
    def __init__(self, cursor):
        self.__class__ = type(cursor.__class__.__name__,
                              (self.__class__, cursor.__class__),
                              {})
        self.__dict__ = cursor.__dict__
        self._cursor = cursor

    def iteritems(self):
        if self._cursor.count() > 0:
            ref = self._cursor.next()
            return iter([(x, ref[x]) for x in ref])
        else:
            return iter([])

    def __getitem__(self, index):
        arr = [x for x in self._dataset]
        item = arr[index]
        self._dataset = iter(arr)
        return item


class Collection(mongomock.Collection):
    def __getattr__(self, name):
        if name == 'database':
            return self._Collection__database

    def find(self, *args, **kwargs):
        if 'read_preference' in kwargs:
            kwargs.pop('read_preference')
        return Cursor(super(Collection, self).find(*args, **kwargs))

    def find_one(self, *args, **kwargs):
        if 'read_preference' in kwargs:
            kwargs.pop('read_preference')
        return super(Collection, self).find_one(*args, **kwargs)

    def update(self, *args, **kwargs):
        super(Collection, self).update(*args, **kwargs)
        return {'n': 1}

    def insert(self, *args, **kwargs):
        for arg in ['w', 'wtimeout', 'j', 'fsync']:
            kwargs.pop(arg, 'foo')
        return super(Collection, self).insert(*args, **kwargs)

    def remove(self, *args, **kwargs):
        return super(Collection, self).remove(*args)


COLLECTIONS = {}


def get_collection(db_name, collection_name):
    mongo_collection = Collection(MockMongoDB(db_name), collection_name)
#    if collection_name in getattr(mongo_fixtures, db_name):
#        name_data_list = getattr(mongo_fixtures, db_name)[collection_name]
    if collection_name in ks_cache:
        name_data_list = ks_cache[collection_name]
        COLLECTIONS.setdefault(db_name, {})
        if collection_name in COLLECTIONS[db_name]:
            return COLLECTIONS[db_name][collection_name]
        for elem in name_data_list:
            mongo_collection.insert(from_dict(elem))
        COLLECTIONS[db_name][collection_name] = mongo_collection
    return mongo_collection


# lets monkey patch mongo
class MockMongoDB(object):
    def __init__(self, dbname):
        self._dbname = dbname
        self.mainpulator = None

    def authenticate(self, username, password):
        pass

    def add_son_manipulator(self, manipulator):
        self.mainpulator = manipulator

    def __getattr__(self, name):
        if name == 'authenticate':
            return self.authenticate
        elif name == 'name':
            return self._dbname
        elif name == 'add_son_manipulator':
            return self.add_son_manipulator
        else:
            return get_collection(self._dbname, name)

    def __getitem__(self, name):
            return get_collection(self._dbname, name)


class MockMongoClient(object):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, dbname):
        return MockMongoDB(dbname)


def pymongo_override():
    import pymongo
    if not pymongo.MongoClient is MockMongoClient:
        pymongo.MongoClient = MockMongoClient


class MongoCache(tests.TestCase):
    def setUp(self):
        super(MongoCache, self).setUp()
        global COLLECTIONS
        COLLECTIONS = {}
        pymongo_override()

    def test_missing_db_hosts(self):
        arguments = {
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password'
        }
        region = make_region()
        self.assertRaises(exception.ValidationError, region.configure,
                          'keystone.cache.mongo',
                          arguments=arguments)

    def test_missing_db_name(self):
        arguments = {
                'db_hosts': 'localhost:27017',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password'
        }
        region = make_region()
        self.assertRaises(exception.ValidationError, region.configure,
                          'keystone.cache.mongo',
                          arguments=arguments)

    def test_missing_cache_collection_name(self):
        arguments = {
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'username': 'test_user',
                'password': 'test_password'
        }
        region = make_region()
        self.assertRaises(exception.ValidationError, region.configure,
                          'keystone.cache.mongo',
                          arguments=arguments)

    def test_missing_replica_set_name(self):
        arguments = {
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password',
                'use_replica': True
        }
        region = make_region()
        self.assertRaises(exception.ValidationError, region.configure,
                          'keystone.cache.mongo',
                          arguments=arguments)

    def test_provided_replica_set_name(self):
        arguments = {
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password',
                'use_replica': True,
                'replicaset_name': 'my_replica'
        }
        make_region().configure('keystone.cache.mongo',
                                arguments=arguments)
        self.assertTrue(True)  # reached here means no initialization error

    def test_cache_configuratin_values_assertion(self):
        arguments = {
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password',
                'use_replica': True,
                'replicaset_name': 'my_replica',
                'mongo_ttl_seconds': 60,
                'ssl': False
        }
        region = make_region().configure('keystone.cache.mongo',
                                         arguments=arguments)
        # There is no proxy so can access MongoCacheBackend directly
        self.assertEquals(region.backend.api.hosts, 'localhost:27017')
        self.assertEquals(region.backend.api.db_name, 'ks_cache')
        self.assertEquals(region.backend.api.cache_collection, 'cache')
        self.assertEquals(region.backend.api.username, 'test_user')
        self.assertEquals(region.backend.api.password, 'test_password')
        self.assertEquals(region.backend.api.use_replica, True)
        self.assertEquals(region.backend.api.replicaset_name, 'my_replica')
        self.assertEquals(region.backend.api.conn_kwargs['ssl'], False)
        self.assertEquals(region.backend.api.ttl_seconds, 60)
        self.assertEquals(region.backend.api.username, 'test_user')

    def test_typical_configuration(self):

        make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password',
                }
        )
        self.assertTrue(True)  # reached here means no initialization error

    def test_backend_get_missing_data(self):

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache'
                }
        )

        random_key = uuid.uuid4().hex
        self.assertEqual(api.NO_VALUE, region.get(random_key))

    def test_backend_set_data(self):

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache'
                }
        )

        random_key = uuid.uuid4().hex
        region.set(random_key, "dummyValue")
        self.assertEqual("dummyValue", region.get(random_key))

    def test_backend_delete_data(self):

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache'
                }
        )

        random_key = uuid.uuid4().hex
        region.set(random_key, "dummyValue")
        self.assertEqual("dummyValue", region.get(random_key))

        region.delete(random_key)
        self.assertEqual(api.NO_VALUE, region.get(random_key))

    def test_backend_multi_set_data(self):

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache'
                }
        )
        random_key = uuid.uuid4().hex
        random_key1 = uuid.uuid4().hex
        random_key2 = uuid.uuid4().hex
        random_key3 = uuid.uuid4().hex
        mapping = {random_key1: 'dummyValue1',
                   random_key2: 'dummyValue2',
                   random_key3: 'dummyValue3'}
        region.set_multi(mapping)
        self.assertEqual(api.NO_VALUE, region.get(random_key))
        self.assertEqual("dummyValue1", region.get(random_key1))
        self.assertEqual("dummyValue2", region.get(random_key2))
        self.assertEqual("dummyValue3", region.get(random_key3))

    def test_backend_multi_delete_data(self):

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments={
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache'
                }
        )
        random_key = uuid.uuid4().hex
        random_key1 = uuid.uuid4().hex
        random_key2 = uuid.uuid4().hex
        random_key3 = uuid.uuid4().hex
        mapping = {random_key1: 'dummyValue1',
                   random_key2: 'dummyValue2',
                   random_key3: 'dummyValue3'}
        region.set_multi(mapping)
        self.assertEqual(api.NO_VALUE, region.get(random_key))
        self.assertEqual("dummyValue1", region.get(random_key1))
        self.assertEqual("dummyValue2", region.get(random_key2))
        self.assertEqual("dummyValue3", region.get(random_key3))
        self.assertEqual(api.NO_VALUE, region.get("InvalidKey"))

        keys = mapping.keys()

        region.delete_multi(keys)
        self.assertEqual(api.NO_VALUE, region.get("InvalidKey"))
        self.assertEqual(api.NO_VALUE, region.get(random_key1))
        self.assertEqual(api.NO_VALUE, region.get(random_key2))
        self.assertEqual(api.NO_VALUE, region.get(random_key3))
