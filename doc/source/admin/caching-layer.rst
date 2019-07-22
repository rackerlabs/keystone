Caching guide
=============

Keystone supports a wide variety of caching options. These options allow
operators to cache certain resources in specific ways or apply a generic
caching strategy to all keystone resources. Caching data within keystone is
imperative to a responsive OpenStack cluster. Keystone's caching strategy is
driven by the `oslo.cache <https://docs.openstack.org/oslo.cache/latest/>`__
library.

This section of the configuration guide describes caching best practices.

Global configuration
--------------------

Keystone exposes `oslo.cache` configuration options. These options are
relatively generic and control the overall behavior of your caching strategy.
You can find these options in the ``[cache]`` section of your ``keystone.conf``
configuration file.

This section includes a system-wide toggle that enables or disables caching.
You want to make sure ``keystone.conf [cache] enabled`` is set to ``true`` if
you want keystone to cache anything at all.

.. code-block:: ini

   [cache]
   enabled=true

Resource configuration
----------------------

In addition to generic configuration options, keystone supplies resource
specific configuration options that describe the behavior for caching within a
specific subsystem. For example, if you want to disable caching of identity
data (e.g., user and groups), you can set ``keystone.conf [identity] caching``
to ``False``. Additionally, you can specify specific timeouts for each
subsystem. For example, setting some resources to have shorter timeouts that
others. These options give you more control over, especially if you don't want
the one-size-fits-all approach available from `oslo.limit`. By default,
keystone enables caching for all subsystems, which is highly recommended.

For example, the following configuration disables all backends with the
exception of the token backend:

.. code-block:: ini

   [cache]
   enabled=true

   [catalog]
   caching=false

   [domain_config]
   caching=false

   [federation]
   caching=false

   [resource]
   caching=false

   [revoke]
   caching=false

   [role]
   caching=false

   [token]
   caching=true

Backend configuration
---------------------

Keystone supports backend drivers for multiple caching backing via
`oslo.cache`. The default backend effectively disables all caching even if
``keystone.conf [cache] enabled`` is set to ``True``. Other options include
Redis and Memcached.  Please be aware of Redis licensing `changes
<https://redislabs.com/blog/redis-labs-modules-license-changes/>`_ if you're
planning on using Redis in your deployment. Note that Redis and Memcached have
very different implementations. Please consult the documentation for each to
understand how their implementations may affect your deployment.

It is important to note the ways in which keystone can use caching backends and
what implications it has on performance. A common deployment strategy is to
deploy a Memcached instance alongside keystone. Keystone can reference a local
copy of Memcached to store data for requests that specific keystone instance
serves. If you're deployment is highly available and scales linearly, this
might not be the most efficient caching option since each keystone instance
caches requests in separate, local, Memcached instances. For example, a request
to ``GET /v3/users/6ec6a3c`` on one keystone node will result in ``6ec6a3c``
being cached locally, but a subsequent request to get the same user from
another keystone server in the same deployment will require a round trip to the
database since other keystone nodes aren't guaranteed to have user ``6ec6a3c``
in their local Memcached instance. In the worst case, each keystone node needs
to cache the same user before the performance benefits take place. To help
mitigate this issue, you can configure keystone to shard cache keys across a
cluster of Memcached servers. Supplying the same backend configuration across
each keystone node allows a cache entry from one keystone node to be visible to
others. Now when a request for ``GET /v3/users/6ec6a3c`` is routed to another
keystone node, it results in a cache hit instead of a miss since all keystone
instances are sharing a common cache. You can take advantage of this by
specifying the same server order for ``keystone.conf [cache]
memcached_servers`` across all keystone nodes.

The following configuration shows how to setup caching to shard cache results
across two different instances of Memcached:

.. code-block:: ini

   [cache]

   enabled = true
   backend = dogpile.cache.memcached
   backend_argument = url:192.168.1.1:11211,url:192.168.1.2:11221

Caching for tokens and tokens validation
----------------------------------------

The token subsystem is OpenStack Identity's most heavily used API. As a result,
all types of tokens benefit from caching, including Fernet tokens. Although
Fernet tokens do not need to be persisted, they should still be cached for
optimal token validation performance. Caching is important for token validation
since token references are rebuilt using a few key pieces of information.
Keystone constructs the token reference by querying individual subsystems and
building a response.

The token system has a separate ``cache_time`` configuration option,
that can be set to a value above or below the global ``expiration_time``
default, allowing for different caching behavior from the other systems
in OpenStack Identity. This option is set in the ``[token]`` section of
the configuration file.

The token revocation list cache time is handled by the configuration
option ``revocation_cache_time`` in the ``[token]`` section. The
revocation list is refreshed whenever a token is revoked. It typically
sees significantly more requests than specific token retrievals or token
validation calls.

Here is a list of actions that are affected by the cached time:

* getting a new token
* revoking tokens
* validating tokens
* checking v3 tokens

The delete token API calls invalidate the cache for the tokens being
acted upon, as well as invalidating the cache for the revoked token list
and the validate/check token calls.

Token caching is configurable independently of the ``revocation_list``
caching. Lifted expiration checks from the token drivers to the token
manager. This ensures that cached tokens will still raise a
``TokenNotFound`` flag when expired.

For cache consistency, all token IDs are transformed into the short
token hash at the provider and token driver level. Some methods have
access to the full ID (PKI Tokens), and some methods do not. Cache
invalidation is inconsistent without token ID normalization.

Caching for non-token resources
-------------------------------

Various other keystone components have a separate ``cache_time`` configuration
option, that can be set to a value above or below the global
``expiration_time`` default, allowing for different caching behavior
from the other systems in Identity service. This option can be set in various
sections (for example, ``[role]`` and ``[resource]``) of the configuration
file.
The create, update, and delete actions for domains, projects and roles
will perform proper invalidations of the cached methods listed above.

For more information about the different back ends (and configuration
options), see:

- `dogpile.cache.memory <https://dogpilecache.sqlalchemy.org/en/latest/api.html#memory-backends>`__

- `dogpile.cache.memcached <https://dogpilecache.sqlalchemy.org/en/latest/api.html#memcached-backends>`__

  .. note::

     The memory back end is not suitable for use in a production
     environment.

- `dogpile.cache.redis <https://dogpilecache.sqlalchemy.org/en/latest/api.html#redis-backends>`__

- `dogpile.cache.dbm <https://dogpilecache.sqlalchemy.org/en/latest/api.html#file-backends>`__

Cache invalidation
------------------

A common concern with caching is relaying inaccurate information after updating
or deleting a resource. Most subsystems within OpenStack Identity invalidate
specific cache entries once they have changed. In cases where a specific cache
entry cannot be invalidated from the cache, the cache region will be
invalidated instead. This invalidates all entries within the cache to prevent
returning stale or misleading data. A subsequent request for the resource will
be fully processed and cached.

.. WARNING::
    Be aware that if a read-only back end is in use for a particular subsystem,
    the cache will not immediately reflect changes performed through the back
    end. Any given change may take up to the ``cache_time`` (if set in the
    subsystem section of the configuration) or the global ``expiration_time``
    (set in the ``[cache]`` section of the configuration) before it is
    reflected. If this type of delay is an issue, we recommend disabling
    caching for that particular subsystem.
