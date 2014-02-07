# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

import collections
import copy
import functools
import six
import uuid

from dogpile.cache import api
from dogpile.cache import region as dp_region

from keystone import exception
from keystone import tests


# Database mock structure sample where 'ks_cache' is database and
# 'cache' is collection. Mock logic uses this for testing.
# '_type_value' is actual dogpile cache data which is tuple
# of payload and metadata (i.e. dogpile.cache.api.CachedValue)
# 1st sample payload (actual value to be cached) is plain dictionary
# and 2nd sample payload is string value
ks_cache = {
    "cache": [
        {
            "value": {
                "_type": "dogpile.cache.api.CachedValue",
                "_type_value": [
                    {
                        "serviceType": "identity",
                        "allVersionsUrl": "https://dummyUrl",
                        "dateLastModified":
                        "ISODDate(2014-02-08T18:39:13.237Z)",
                        "serviceName": "Identity",
                        "enabled": "True",
                    },
                    {
                        "v": 1,
                        "ct": 1391828529.061648
                    }
                ]
            },
            "key": "get_service_by_name",
            "doc_date": "ISODate(2014-02-08T03:02:09.061Z)"
        },
        {
            "value": {
                "_type": "dogpile.cache.api.CachedValue",
                "_type_value": [
                    "dummyValue",
                    {
                        "v": 1,
                        "ct": 1391828529.257848
                    }
                ]
            },
            "key": "a844cf5b941f45b7aef6630754862cd7",
            "doc_date": "ISODate(2014-02-08T03:02:10.161Z)"
        }
    ]
}


COLLECTIONS = {}
SON_MANIPULATOR = None


class MockCursor(object):

    def __init__(self, collection, dataset_factory):
        super(MockCursor, self).__init__()
        self.collection = collection
        self._factory = dataset_factory
        self._dataset = self._factory()
        self._limit = None
        self._skip = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._skip:
            for _ in range(self._skip):
                next(self._dataset)
            self._skip = None
        if self._limit is not None and self._limit <= 0:
            raise StopIteration()
        if self._limit is not None:
            self._limit -= 1
        return next(self._dataset)

    next = __next__

    def __getitem__(self, index):
        arr = [x for x in self._dataset]
        self._dataset = iter(arr)
        return arr[index]


class MockCollection(object):

    def __init__(self, db, name):
        super(MockCollection, self).__init__()
        self.name = name
        self._collection_database = db
        self._documents = {}

    def __getattr__(self, name):
        if name == 'database':
            return self._collection_database

    def ensure_index(self, key_or_list, *args, **kwargs):
        pass

    def find_one(self, spec_or_id=None, *args, **kwargs):
        if spec_or_id is None:
            spec_or_id = {}
        if not isinstance(spec_or_id, collections.Mapping):
            spec_or_id = {'_id': spec_or_id}

        try:
            return next(self.find(spec_or_id, *args, **kwargs))
        except StopIteration:
            return None

    def find(self, spec=None):
        return MockCursor(self, functools.partial(self._get_dataset, spec))

    def _get_dataset(self, spec):
        dataset = (self._copy_doc(document, dict) for document in
                   self._iter_documents(spec))
        return dataset

    def _iter_documents(self, spec=None):
        return (SON_MANIPULATOR.transform_outgoing(document, self) for
                document in six.itervalues(self._documents)
                if self._apply_filter(document, spec))

    def _apply_filter(self, document, query):
        for key, search in query.iteritems():
            doc_val = document.get(key)
            if isinstance(search, dict):
                op_dict = {'$in': lambda dv, sv: dv in sv}
                is_match = all(
                    op_str in op_dict and op_dict[op_str](doc_val, search_val)
                    for op_str, search_val in six.iteritems(search)
                )
            else:
                is_match = doc_val == search

        return is_match

    def _copy_doc(self, obj, container):
        if isinstance(obj, list):
            new = []
            for item in obj:
                new.append(self._copy_doc(item, container))
            return new
        if isinstance(obj, dict):
            new = container()
            for key, value in obj.items():
                new[key] = self._copy_doc(value, container)
            return new
        else:
            return copy.copy(obj)

    def insert(self, data, manipulate=True, **kwargs):
        if isinstance(data, list):
            return [self._insert(element) for element in data]
        return self._insert(data)

    def save(self, data, manipulate=True, **kwargs):
        return self._insert(data)

    def _insert(self, data):
        if '_id' not in data:
            data['_id'] = uuid.uuid4().hex
        object_id = data['_id']
        self._documents[object_id] = self._internalize_dict(data)
        return object_id

    def find_and_modify(self, spec, document, upsert=False, **kwargs):
        self.update(spec, document, upsert, **kwargs)

    def update(self, spec, document, upsert=False, **kwargs):

        existing_docs = [doc for doc in six.itervalues(self._documents)
                         if self._apply_filter(doc, spec)]
        if existing_docs:
            existing_doc = existing_docs[0]  # should find only 1 match
            _id = existing_doc['_id']
            existing_doc.clear()
            existing_doc['_id'] = _id
            existing_doc.update(self._internalize_dict(document))
        elif upsert:
            existing_doc = self._documents[self._insert(document)]

    def _internalize_dict(self, d):
        return dict((k, copy.deepcopy(v)) for k, v in six.iteritems(d))

    def remove(self, spec_or_id=None, search_filter=None):
        """Remove objects matching spec_or_id from the collection."""
        if spec_or_id is None:
            spec_or_id = search_filter if search_filter else {}
        if not isinstance(spec_or_id, dict):
            spec_or_id = {'_id': spec_or_id}
        to_delete = list(self.find(spec=spec_or_id))
        for doc in to_delete:
            doc_id = doc['_id']
            del self._documents[doc_id]

        return {
            "connectionId": uuid.uuid4().hex,
            "n": len(to_delete),
            "ok": 1.0,
            "err": None,
        }


class MockMongoDB(object):
    def __init__(self, dbname):
        self._dbname = dbname
        self.mainpulator = None

    def authenticate(self, username, password):
        pass

    def add_son_manipulator(self, manipulator):
        global SON_MANIPULATOR
        SON_MANIPULATOR = manipulator

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


def get_collection(db_name, collection_name):
    mongo_collection = MockCollection(MockMongoDB(db_name), collection_name)
    if collection_name in ks_cache:
        name_data_list = ks_cache[collection_name]
        COLLECTIONS.setdefault(db_name, {})
        if collection_name in COLLECTIONS[db_name]:
            return COLLECTIONS[db_name][collection_name]
        for elem in name_data_list:
            mongo_collection.insert(elem)
        COLLECTIONS[db_name][collection_name] = mongo_collection
    return mongo_collection


def pymongo_override():
    global pymongo
    import pymongo
    if pymongo.MongoClient is not MockMongoClient:
        pymongo.MongoClient = MockMongoClient
    if pymongo.MongoReplicaSetClient is not MockMongoClient:
        pymongo.MongoClient = MockMongoClient


class MyTransformer(object):
    '''Can inherit from keystone.common.cache.backends.mongo.BaseTransform

    Added such to avoid explicit import dependency
    '''
    def __init__(self):
        pass


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
        region = dp_region.make_region()
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
        region = dp_region.make_region()
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
        region = dp_region.make_region()
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
        region = dp_region.make_region()
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
        dp_region.make_region().configure('keystone.cache.mongo',
                                          arguments=arguments)
        self.assertTrue(True)  # reached here means no initialization error

    def test_incorrect_mongo_ttl_seconds(self):
        arguments = {
            'db_hosts': 'localhost:27017',
            'db_name': 'ks_cache',
            'cache_collection': 'cache_container_2',
            'username': 'test_user',
            'password': 'test_password',
            'mongo_ttl_seconds': 'sixty'
        }
        region = dp_region.make_region().configure(
            'keystone.cache.mongo',
            arguments=arguments
        )
        self.assertRaises(exception.ValidationError, region.get,
                          'anyKey'),

    def test_cache_configuration_values_assertion(self):
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
        region = dp_region.make_region().configure('keystone.cache.mongo',
                                                   arguments=arguments)
        # There is no proxy so can access MongoCacheBackend directly
        self.assertEqual(region.backend.api.hosts, 'localhost:27017')
        self.assertEqual(region.backend.api.db_name, 'ks_cache')
        self.assertEqual(region.backend.api.cache_collection, 'cache')
        self.assertEqual(region.backend.api.username, 'test_user')
        self.assertEqual(region.backend.api.password, 'test_password')
        self.assertEqual(region.backend.api.use_replica, True)
        self.assertEqual(region.backend.api.replicaset_name, 'my_replica')
        self.assertEqual(region.backend.api.conn_kwargs['ssl'], False)
        self.assertEqual(region.backend.api.ttl_seconds, 60)

    def test_multiple_region_cache_configuration(self):
        arguments1 = {
            'db_hosts': 'localhost:27017',
            'db_name': 'ks_cache',
            'cache_collection': 'cache_region1',
            'username': 'test_user',
            'password': 'test_password'
        }
        region1 = dp_region.make_region().configure('keystone.cache.mongo',
                                                    arguments=arguments1)
        # There is no proxy so can access MongoCacheBackend directly
        self.assertEqual(region1.backend.api.hosts, 'localhost:27017')
        self.assertEqual(region1.backend.api.db_name, 'ks_cache')
        self.assertEqual(region1.backend.api.cache_collection, 'cache_region1')
        self.assertEqual(region1.backend.api.username, 'test_user')
        self.assertEqual(region1.backend.api.password, 'test_password')

        arguments2 = {
            'db_hosts': 'localhost:27420',
            'db_name': 'ks_cache',
            'cache_collection': 'cache_region2',
            'son_manipulator': 'test_cache_backend_mongo.MyTransformer'
        }
        region2 = dp_region.make_region().configure('keystone.cache.mongo',
                                                    arguments=arguments2)
        # There is no proxy so can access MongoCacheBackend directly
        self.assertEqual(region2.backend.api.hosts, 'localhost:27420')
        self.assertEqual(region2.backend.api.db_name, 'ks_cache')
        self.assertEqual(region2.backend.api.cache_collection, 'cache_region2')

    def test_typical_configuration(self):

        dp_region.make_region().configure(
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

        region = dp_region.make_region().configure(
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

        region = dp_region.make_region().configure(
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

    def test_backend_set_same_key_multiple_times(self):

        region = dp_region.make_region().configure(
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

        dict_value = {'key1': 'value1'}
        region.set(random_key, dict_value)
        self.assertEqual(dict_value, region.get(random_key))

        region.set(random_key, "dummyValue2")
        self.assertEqual("dummyValue2", region.get(random_key))

    def test_backend_multi_set_data(self):

        region = dp_region.make_region().configure(
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

    def test_backend_multi_set_should_update_existing(self):

        region = dp_region.make_region().configure(
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

        mapping = {random_key1: 'dummyValue4',
                   random_key2: 'dummyValue5'}
        region.set_multi(mapping)
        self.assertEqual(api.NO_VALUE, region.get(random_key))
        self.assertEqual("dummyValue4", region.get(random_key1))
        self.assertEqual("dummyValue5", region.get(random_key2))
        self.assertEqual("dummyValue3", region.get(random_key3))

    def test_backend_delete_data(self):

        region = dp_region.make_region().configure(
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

    def test_backend_multi_delete_data(self):

        region = dp_region.make_region().configure(
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
