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

import datetime

from dogpile.cache import api
from dogpile.cache import util as dp_util
import six

from keystone import exception
from keystone.openstack.common import importutils
from keystone.openstack.common import log
from keystone.openstack.common import timeutils


NO_VALUE = api.NO_VALUE
LOG = log.getLogger(__name__)


class MongoCacheBackend(api.CacheBackend):
    """A MongoDB based caching backend implementing dogpile backend APIs

    Arguments accepted in the arguments dictionary:

    :param db_hosts: string. Required parameter. hostname or IP address of
    the instance to connect to, or a MongoDB connection URI, or a list of
    hostnames / MongoDB connection URIs.

    :param db_name: string, Required parameter. the name of the database to
    be used.

    :param cache_collection: string. Required parameter. the name of
    collection to store cached data.
    :Note Different collection name can be provided if there is need to
    create separate container (i.e. collection) for cache data. So region
    configuration is done per collection.

    Following are optional parameters for MongoDB backend configuration,

    :param username: string, the name of the user to authenticate.
    :param password: string, the password of the user to authenticate.

    :param max_pool_size: integer,  The maximum number of connections that
    the pool will open simultaneously. By default the pool size is 10.

    :param use_replica: boolean, flag to indicate if replica client to be
    used. Default is False.
    :param replicaset_name: string, name of replica set. Becomes required
    if `use_replica` is `True`

    :param son_manipulator: string, name of class with module name which
    implements MongoDB SONManipulator.
    SONManipulator is used to manipulate custom data types as they are saved
    or retrieved from MongoDB. Custom impl is only needed if cached data is
    custom class and needs transformations when saving or reading from db.
    If dogpile cached value contains built-in data types, then BaseTransform
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
    you are setting mongo_ttl_seconds, you will want to make sure it is
    greater than expiration_time by at least enough seconds for new values
    to be generated, else the value would not be available during a
    regeneration, forcing all threads to wait for a regeneration each time
    a value expires.

    :param ssl: boolean, If True, create the connection to the server
    using SSL. Default is `False`.
    :param ssl_keyfile: string, The private keyfile used to identify the
    local connection against mongod. If included with the certfile then
    only the `ssl_certfile` is needed. Used only when `ssl` is `True`.
    :param ssl_certfile: string, The certificate file used to identify the
    local connection against mongod. Used only when `ssl` is `True`.
    :param ssl_ca_certs: string, The ca_certs file contains a set of
    concatenated 'certification authority' certificates, which are used to
    validate certificates passed from the other end of the connection.
    Used only when `ssl` is `True`.
    :param ssl_cert_reqs: string, The parameter cert_reqs specifies whether
    a certificate is required from the other side of the connection, and
    whether it will be validated if provided. It must be one of the three
    values ``ssl.CERT_NONE`` (certificates ignored), ``ssl.CERT_OPTIONAL``
    (not required, but validated if provided), or
    ``ssl.CERT_REQUIRED`` (required and validated). If the value of this
    parameter is not ``ssl.CERT_NONE``, then the ssl_ca_certs parameter must
    point to a file of CA certificates. Used only when `ssl` is `True`.

    Rest of arguments are passed to mongo calls for read, write and remove.
    So related options can be specified to pass to these operations.

    Further details of various supported arguments can be referred from
    <http://api.mongodb.org/python/current/api/pymongo/>

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
    """

    def __init__(self, arguments):
        self.api = MongoApi(arguments)

    @dp_util.memoized_property
    def client(self):
        self.api.get_cache_collection()
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
    """Class for collecting and parsing mongo specific arguments.

    The arguments passed in are separated out in connection specific setting
    and rest of arguments are passed to create/update/delete db operations.
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
            msg = _('cache_collection name is required')
            raise exception.ValidationError(message=msg)

        self.son_manipulator = arguments.pop("son_manipulator", None)
        self.username = arguments.pop("username", None)
        self.password = arguments.pop("password", None)
        self.max_pool_size = arguments.pop("max_pool_size", 10)

        self.use_replica = arguments.pop("use_replica", False)
        if self.use_replica:
            if arguments.get("replicaset_name") is None:
                msg = _('replicaset_name required when use_replica is True')
                raise exception.ValidationError(message=msg)
            self.replicaset_name = arguments.get("replicaset_name")

        self.conn_kwargs['ssl'] = arguments.pop('ssl', False)
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
                    self._ssl_cert_req_type(ssl_cert_reqs)

        # set if mongo collection needs to be TTL type.
        # This needs to be max ttl for any cache entry.
        # By default, -1 means don't use TTL collection.
        # With ttl set, it creates related index and have doc_date field with
        # needed expiration interval
        self.ttl_seconds = arguments.pop("mongo_ttl_seconds", -1)
        try:
            self.ttl_seconds = int(self.ttl_seconds)
        except ValueError:
            msg = _('integer value expected for mongo_ttl_seconds')
            raise exception.ValidationError(message=msg)

        # rest of arguments are passed to mongo crud calls
        self.meth_kwargs = arguments

    def _ssl_cert_req_type(self, req_type):
        try:
            import ssl
        except ImportError:
            msg = _('no ssl support available')
            raise exception.ValidationError(msg)
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


class MongoApi(object):
    """Class handling MongoDB specific functionality

    This class uses PyMongo APIs internally to create database connection
    with configured pool size, ensures unique index on key, does database
    authentication and ensure TTL collection index if configured so.
    This class also serves as handle to cache collection for dogpile cache APIs
    """

    def __init__(self, arguments):
        margs = MongoArgs(arguments)
        margs_kv = vars(margs)
        for arg_key, arg_value in six.iteritems(margs_kv):
            setattr(self, arg_key, arg_value)
            msg = _("MongoDB cache backend configuration, %(key)s : %(value)s"
                    ) % {'key': arg_key, 'value': arg_value}
            LOG.info(msg)
        self._data_manipulator = None
        self._mongo_colls = {}

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

        self._assign_data_mainpulator()
        database.add_son_manipulator(self._data_manipulator)
        if self.username and self.password:
            database.authenticate(self.username, self.password)
        return database

    def _assign_data_mainpulator(self):
        if self._data_manipulator is None:
            if self.son_manipulator:
                self._data_manipulator = importutils.import_object(
                    self.son_manipulator)
            else:
                self._data_manipulator = BaseTransform()

    def _get_doc_date(self):
        if self.ttl_seconds > 0:
            expire_delta = datetime.timedelta(seconds=self.ttl_seconds)
            doc_date = timeutils.utcnow() + expire_delta
        else:
            doc_date = timeutils.utcnow()
        return doc_date

    def get_cache_collection(self):
        if self.cache_collection not in self._mongo_colls:
            db = self._get_db()
            coll = getattr(db, self.cache_collection)

            # create or ensure unique index for 'key' field
            coll.ensure_index('key', unique=True)
            if self.ttl_seconds > 0:
                kwargs = {'expireAfterSeconds': self.ttl_seconds}
                coll.ensure_index('doc_date', cache_for=5, **kwargs)
            else:
                self._validate_ttl_index(coll, self.cache_collection,
                                         self.ttl_seconds)
            self._mongo_colls[self.cache_collection] = coll

        return self._mongo_colls[self.cache_collection]

    def _get_cache_entry(self, key, value, meta, doc_date):
        """MongoDB cache data representation

        Document to be stored which has additional date field for mongo TTL
        support.
        """
        return dict(key=key, value=value, meta=meta, doc_date=doc_date)

    def _validate_ttl_index(self, collection, coll_name, ttl_seconds):
        """Checks if existing TTL index is removed on a collection.

        This logs warning when existing collection has TTL index defined and
        updated cache configuration tries to disable this with
        `` mongo_ttl_seconds < -1``. In that case, existing index needs
        to be addressed first to make new configuration effective.
        Refer to MongoDB documentation around TTL index for further details.
        """
        indexes = collection.index_information()
        for indx_name, index_data in six.iteritems(indexes):
            if all(k in index_data for k in ('key', 'expireAfterSeconds')):
                existing_value = index_data['expireAfterSeconds']
                fld_present = 'doc_date' in index_data['key'][0]
                if fld_present and existing_value > -1 and ttl_seconds < 1:
                    msg = _('TTL index already exists on db collection '
                            '<%(c_name)s>, address index <%(indx_name)s> first'
                            ' to make updated mongo_ttl_seconds value to be '
                            ' effective'
                            ) % {'c_name': coll_name, 'indx_name': indx_name}
                    LOG.warn(msg)

    def get(self, key):
        critieria = {'key': key}
        result = self.get_cache_collection().find_one(spec_or_id=critieria,
                                                      **self.meth_kwargs)
        if result:
            return result['value']
        else:
            return None

    def get_multi(self, keys):
        db_results = self._get_results_as_dict(keys)
        results_dict = dict((doc['key'], doc['value']) for doc in
                            six.itervalues(db_results))
        return results_dict

    def _get_results_as_dict(self, keys):
        critieria = {'key': {'$in': keys}}
        db_results = self.get_cache_collection().find(spec=critieria,
                                                      **self.meth_kwargs)
        dict_results = dict((doc['key'], doc) for doc in db_results)
        return dict_results

    def set(self, key, value):
        doc_date = self._get_doc_date()
        ref = self._get_cache_entry(key, value.payload, value.metadata,
                                    doc_date)
        self._assign_data_mainpulator()  # assign if not initialized
        ref = self._data_manipulator.transform_incoming(ref, self)
        spec = {'key': key}
        # find and modify does not have manipulator support
        # so need to do conversion as part of input document
        self.get_cache_collection().find_and_modify(spec, ref, upsert=True,
                                                    **self.meth_kwargs)

    def set_multi(self, mapping):
        """Insert multiple documents specified as key, value pairs

        In this case, multiple documents can be added via insert provided they
        do not exist.
        Update of multiple existing documents is done one by one
        """
        doc_date = self._get_doc_date()
        insert_refs = []
        update_refs = []
        existing_docs = self._get_results_as_dict(mapping.keys())
        for key, value in mapping.items():
            ref = self._get_cache_entry(key, value.payload, value.metadata,
                                        doc_date)
            if key in existing_docs:
                ref['_id'] = existing_docs[key]['_id']
                update_refs.append(ref)
            else:
                insert_refs.append(ref)
        if insert_refs:
            self.get_cache_collection().insert(insert_refs, manipulate=True,
                                               **self.meth_kwargs)
        for upd_doc in update_refs:
            self.get_cache_collection().save(upd_doc, manipulate=True,
                                             **self.meth_kwargs)

    def delete(self, key):
        critieria = {'key': key}
        self.get_cache_collection().remove(spec_or_id=critieria,
                                           **self.meth_kwargs)

    def delete_multi(self, keys):
        critieria = {'key': {'$in': keys}}
        self.get_cache_collection().remove(spec_or_id=critieria,
                                           **self.meth_kwargs)


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
    """Base transformation class to store and read dogpile cached data
    from MongoDB.

    This is needed as dogpile internally stores data as a custom class
    i.e. dogpile.cache.api.CachedValue

    Note: Custom manipulator needs to always override ``transform_incoming``
    and ``transform_outgoing`` methods even if there customization logic
    needs to be same as super() class as MongoDB requires different instance
    and super methods before it includes these methods in its logic
    """

    def transform_incoming(self, son, collection):
        """Used while saving data to MongoDB."""
        for (key, value) in son.items():
            if isinstance(value, api.CachedValue):
                son[key] = value.payload  # key is 'value' field here
                son["meta"] = value.metadata
            elif isinstance(value, dict):  # Make sure we recurse into sub-docs
                son[key] = self.transform_incoming(value, collection)
        return son

    def transform_outgoing(self, son, collection):
        """Used while reading data from MongoDB."""
        metadata = None
        # make sure its top level dictionary with all expected fields names
        # present
        if isinstance(son, dict) and all(k in son for k in
                                         ('key', 'value', 'meta', 'doc_date')):
            payload = son.pop("value", None)
            metadata = son.pop("meta", None)
        for (key, value) in son.items():
            if isinstance(value, dict):
                son[key] = self.transform_outgoing(value, collection)
        if metadata is not None:
            son["value"] = api.CachedValue(payload, metadata)
        return son
