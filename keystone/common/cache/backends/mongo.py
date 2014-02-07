# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014 OpenStack Foundation
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

import datetime
from dogpile.cache import api
from dogpile.cache import util as dp_util

from keystone import exception
from keystone.openstack.common import importutils
from keystone.openstack.common import timeutils

NO_VALUE = api.NO_VALUE
HAS_SSL = True
try:
    import ssl
except ImportError:
    HAS_SSL = False


class MongoCacheBackend(api.CacheBackend):
    """A mongo based backend which internally uses pymongo api
        <http://api.mongodb.org/python/current/api/pymongo/>
        to implement dogpile backend apis

        A typical configuration using username/password::

        <code>
        from dogpile.cache import make_region

        region = make_region().configure(
            'keystone.cache.mongo',
            arguments = {
                'db_hosts': 'localhost:27017',
                'db_name': 'ks_cache',
                'cache_collection': 'cache',
                'username': 'test_user',
                'password': 'test_password',

                # optional arguments
                'son_manipulator': 'my_son_manipulator_impl'
                }
        )

        </code>

        Arguments accepted in the arguments dictionary:

        :param db_hosts: string. Required parameter. hostname or IP address of
        the instance to connect to, or a mongodb URI, or a list of
        hostnames / mongodb URIs.

        :param db_name: string, Required parameter. the name of the database to
        be used.

        :param cache_collection: string. Required parameter. the name of
        collection to store cached data.

        Following are optional parameters for mongo backend configuration,

        :param username: string, the name of the user to authenticate.
        :param password: string, the password of the user to authenticate.

        :param max_pool_size: integer,  The maximum number of connections that
        the pool will open simultaneously. By default the pool size is 10.

        :param use_replica: boolean, flag to indicate if replica client to be
        used. Default is False.
        :param replicaset_name: string, name of replica set. Becomes required
        if use_replica is True

        :param son_manipulator: string, name of class with module name which
        implements mongo SONManipulator.
        SONManipulator is used to manipulate custom datatypes as they are saved
        or retrieved from MongoDB. Custom impl is only needed if cached data is
        custom class and needs transformations when saving or reading from db.
        If dogpile cached value contains built-in datatypes, then BaseTransform
        class is sufficient as it already handles dogpile CachedValue class
        transformation.

        :param mongo_ttl_seconds: integer, interval in seconds to indicate
        maximum time-to-live value. If value is greater than 0, then its
        assumed that cache_collection needs to be TTL type (has index at
        'doc_date' field). By default, the value is -1 and its disabled.
        Reference: <http://docs.mongodb.org/manual/tutorial/expire-data/>

        :Note: This parameter is different from Dogpile own
        expiration_time, which is the number of seconds after which Dogpile
        will consider the value to be expired. When Dogpile considers a value
        to be expired, it continues to use the value until generation of a new
        value is complete, when using CacheRegion.get_or_create().Therefore, if
        you are setting memcached_expire_time, you will want to make sure it is
        greater than expiration_time by at least enough seconds for new values
        to be generated, else the value would not be available during a
        regeneration, forcing all threads to wait for a regeneration each time
        a value expires.

        :param ssl: boolean, If True, create the connection to the server
        using SSL. Default is False.
        :param ssl_keyfile: string, The private keyfile used to identify the
        local connection against mongod. If included with the certfile` then
        only the ``ssl_certfile is needed. Used only when 'ssl' is True.
        :param ssl_certfile: string, The certificate file used to identify the
        local connection against mongod. Used only when 'ssl' is True.
        :param ssl_ca_certs: string, The ca_certs file contains a set of
        concatenated 'certification authority' certificates, which are used to
        validate certificates passed from the other end of the connection.
        Used only when 'ssl' is True.
        :param ssl_certfile: string, The parameter cert_reqs specifies whether
        a certificate is required from the other side of the connection, and
        whether it will be validated if provided. It must be one of the three
        values ssl.CERT_NONE (certificates ignored), ssl.CERT_OPTIONAL
        (not required, but validated if provided), or
        ssl.CERT_REQUIRED (required and validated). If the value of this
        parameter is not ssl.CERT_NONE, then the ssl_ca_certs parameter must
        point to a file of CA certificates. Used only when 'ssl' is True.

        rest of arguments are passed to mongo calls for read, write and remove.
        So related options can be specified to pass to these operations.
    """

    def __init__(self, arguments):
        self.api = MongoApi(arguments)

    @property
    def client(self):
        return self._create_client

    @dp_util.memoized_property
    def _create_client(self):
        self.api._get_cache_collection()
        return self.api

    def get(self, key):
        value = self.client.get(key)
        if value is None:
            return NO_VALUE
        else:
            return value

    def get_multi(self, keys):
        values = self.client.get_multi(keys)
        return [
            NO_VALUE if key not in values
            else values[key] for key in keys
        ]

    def set(self, key, value):
        self.client.set(key, value)

    def set_multi(self, mapping):
        self.client.set_multi(mapping)

    def delete(self, key):
        self.client.delete(key)

    def delete_multi(self, keys):
        self.client.delete_multi(keys)


class MongoArgs(object):
    """Class for collecting and parsing mongo specific arguments which are used
    for establishing connection, db settings and passing to db operations.
    """
    def __init__(self, arguments):

        self.conn_kwargs = {}  # connection specific arguments

        self.hosts = arguments.pop("db_hosts", None)
        if self.hosts is None:
            msg = _('db_hosts value is required')
            raise exception.ValidationError(message=msg)

        self.db_name = arguments.pop("db_name", None)
        if self.db_name is None:
            msg = _('database db_name is required')
            raise exception.ValidationError(message=msg)

        self.cache_collection = arguments.pop("cache_collection", None)
        if self.cache_collection is None:
            msg = _('cache collection name is required')
            raise exception.ValidationError(message=msg)

        self.son_manipulator = arguments.pop("son_manipulator", None)
        self.username = arguments.pop("username", None)
        self.password = arguments.pop("password", None)
        self.max_pool_size = arguments.pop("max_pool_size", 10)

        self.use_replica = arguments.pop("use_replica", False)
        if self.use_replica:
            if arguments.get("replicaset_name") is None:
                msg = _('replica name required when replica use is enabled')
                raise exception.ValidationError(message=msg)
            self.replicaset_name = arguments.get("replicaset_name")

        self.conn_kwargs['ssl'] = arguments.pop('ssl', False)
        if self.conn_kwargs['ssl'] and not HAS_SSL:
            raise ValueError('no ssl support available!')
        if self.conn_kwargs['ssl']:
            ssl_keyfile = arguments.pop('ssl_keyfile', None)
            ssl_certfile = arguments.pop('ssl_certfile', None)
            ssl_ca_certs = arguments.pop('ssl_ca_certs', None)
            ssl_cert_reqs = arguments.pop('ssl_cert_reqs', None)
            if ssl_keyfile:
                self.conn_kwargs['ssl_keyfile'] = ssl_keyfile
            if ssl_certfile:
                self.conn_kwargs['ssl_certfile'] = ssl_certfile
            if ssl_ca_certs:
                self.conn_kwargs['ssl_ca_certs'] = ssl_ca_certs
            if ssl_cert_reqs:
                self.conn_kwargs['ssl_cert_reqs'] = \
                    ssl_cert_req_type(ssl_cert_reqs)

        # set if mongo collection needs to be TTL type
        # This needs to be max ttl for any cache entry.
        # By default, -1 means don't use TTL collection, create related
        # index and have doc_date field with needed expiration interval
        self.ttl_seconds = arguments.pop("mongo_ttl_seconds", -1)

        # rest of arguments are passed to mongo crud calls
        self.meth_kwargs = arguments


class CacheEntry(object):
    '''Document to be stored which has additional date field for mongo TTL
    support if needed.
    '''

    def __init__(self, key, cached_value=None, doc_date=None):
        self.key = key
        self.value = cached_value
        self.doc_date = doc_date

    def to_dict(self):
        return self.__dict__


class MongoApi(MongoArgs):
    '''Class handling mongo specific functionality which includes
    creating connection, configuring pool size, authenticating to database,
    and creating handle to cache collection for dogpile cache APIs
    '''
    _COLLS = {}
    _DB = None

    def __init__(self, arguments):
        super(MongoApi, self).__init__(arguments)

    def _get_db(self):
        # defer imports until backend is used
        global pymongo
        import pymongo
        if self.use_replica:
            connection = pymongo.MongoReplicaSetClient(
                host=self.hosts, replicaSet=self.replicaset_name,
                max_pool_size=self.max_pool_size, **self.conn_kwargs)
        else:  # used for standalone node or mongos in sharded setup
            connection = pymongo.MongoClient(
                host=self.hosts, max_pool_size=self.max_pool_size,
                **self.conn_kwargs)

        database = getattr(connection, self.db_name)

        if self.son_manipulator:  # check if custom manipulator is there
            son_manipulator = importutils.import_object(self.son_manipulator)
            database.add_son_manipulator(son_manipulator)
        else:
            database.add_son_manipulator(BaseTransform())
        if self.username and self.password:
            database.authenticate(self.username, self.password)
        return database

    def _get_cache_collection(self):
        if self.cache_collection not in self._COLLS:
            if self._DB is None:
                DB = self._get_db()
            coll = getattr(DB, self.cache_collection)
            try:
                self.ttl_seconds = int(self.ttl_seconds)
            except ValueError:
                msg = _('integer value expected for mongo_ttl_seconds')
                raise exception.ValidationError(message=msg)

            # create or ensure unique index for 'key' field
            coll.ensure_index('key', unique=True)
            if self.ttl_seconds > 0:
                coll.ensure_index({'doc_date': 1},
                                  {'expireAfterSeconds': self.ttl_seconds})
            self._COLLS[self.cache_collection] = coll

        return self._COLLS[self.cache_collection]

    def _get_doc_date(self):
        if self.ttl_seconds > 0:
            expire_delta = datetime.timedelta(seconds=self.ttl_seconds)
            doc_date = timeutils.utcnow() + expire_delta
        else:
            doc_date = timeutils.utcnow()
        return doc_date

    def get(self, key):
        critieria = {'key': key}
        result = self._get_cache_collection().find_one(spec_or_id=critieria,
                                                       **self.meth_kwargs)
        if result:
            return result['value']
        else:
            return None

    def get_multi(self, keys):
        critieria = {'keys': {'$in': keys}}
        db_results = self._get_cache_collection().find(spec=critieria,
                                                       **self.meth_kwargs)
        results_dict = {}
        if db_results:
            for db_result in db_results:
                results_dict[db_result['key']] = \
                    results_dict.append(db_result['value'])
        return results_dict

    def set(self, key, value):
        doc_date = self._get_doc_date()
        ref = CacheEntry(key, value, doc_date).to_dict()

        self._get_cache_collection().insert(ref, **self.meth_kwargs)

    def set_multi(self, mapping):
        doc_date = self._get_doc_date()
        refs = []
        for key, value in mapping.items():
            ref = CacheEntry(key, value, doc_date).to_dict()
            refs.append(ref)

        self._get_cache_collection().insert(refs, **self.meth_kwargs)

    def delete(self, key):
        critieria = {'key': key}
        self._get_cache_collection().remove(spec_or_id=critieria,
                                            **self.meth_kwargs)

    def delete_multi(self, keys):
        critieria = {'key': {'$in': keys}}
        self._get_cache_collection().remove(spec_or_id=critieria,
                                            **self.meth_kwargs)


def ssl_cert_req_type(req_type):
    req_type = req_type.upper()
    try:
        return {
            'NONE': ssl.CERT_NONE,
            'OPTIONAL': ssl.CERT_OPTIONAL,
            'REQUIRED': ssl.CERT_REQUIRED
        }[req_type]
    except KeyError:
        msg = _('Invalid ssl_cert_reqs value of %s, must be one of '
                'ssl.CERT_NONE, ssl.CERT_OPTIONAL, ssl.CERT_REQUIRED'
                ) % (req_type)
        raise exception.ValidationError(message=msg)


class NoOpManipulator(object):
    """Manipulator doing nothing

    Providing base as a hack to avoid import dependency of pymongo specific
    class i.e. pymongo.son_manipulator.SONManipulator
    """
    def transform_incoming(self, son, collection):
        pass

    def transform_outgoing(self, son, collection):
        pass

    def will_copy(self):
        return False


class BaseTransform(NoOpManipulator):
    '''Base transformation class to store and read dogpile cached data
    from mongodb. This is needed as dogpile internally stores data as
    a custom class i.e. dogpile.cache.api.CachedValue
    '''

    def __init__(self):
        tmp = api.CachedValue.__new__(api.CachedValue, "", "")
        self._cv_classname = BaseTransform._clz_name(tmp.__class__)

    @staticmethod
    def _clz_name(clz):
        return '%s.%s' % (clz.__module__, clz.__name__)

    def transform_incoming(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, api.CachedValue):
                payload = value.payload
                son[key] = {"_type": BaseTransform._clz_name(value.__class__),
                            "_type_value": (payload, value.metadata)}
            elif isinstance(value, dict):  # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
        return son

    def encode_custom(self, value):
        pass

    def transform_outgoing(self, son, collection):
        for (key, value) in son.items():
            if isinstance(value, dict):
                if "_type" in value and value["_type"] == self._cv_classname:
                    son[key] = self.decode_custom(value)
                else:  # Again, make sure to recurse into sub-docs
                    son[key] = self.transform_outgoing(value, collection)
        return son

    def decode_custom(self, document):
        # need to use index as document is a dictionary and not a object
        payload = document['_type_value'][0]
        return api.CachedValue.__new__(api.CachedValue, payload,
                                       document['_type_value'][1])
