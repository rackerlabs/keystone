..
      Copyright 2011 OpenStack, LLC
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========
Backends
========

Keystone supports multiple types of data stores for things like users, tenants, and
tokens, including SQL, LDAP, and memcache.

SQL
===

In the default backend configuration (SQL-only), Keystone depends on the following database tables.

`users`
-------

`id`
    Auto-incremented primary key
`name`
    Unqiue username
`password`
    TODO: Why do we have this column *and* the `credentials` table?
`email`
    Email address
`enabled`
    If false, the user is unable to authenticate
`tenant_id`
    Default tenant for the user

`tenants`
---------

`id`
    Auto-incremented primary key
`name`
    Unique string identifying the tenant
`desc`
    Description of the tenant
`enabled`
    If false, users are unable to scope to the tenant

`roles`
-------

`id`
    Auto-incremented primary key
`name`
    Short name of the role
`desc`
    Description of the role
`service_id`
    References the service that owns the role

`user_roles`
------------

Indicates roles that have been granted to users (optionally, within the scope of a tenant).

`id`
    Primary key (TODO: why is this not auto-incremented?)
`user_id`
    References the user being granted a role
`role_id`
    References the granted role
`tenant_id`
    References a tenant upon which this grant is applies

`services`
----------

`id`
    Auto-incremented primary key
`name`
    Unique name of the service
`type`
    Indicates the type of service (e.g. `compute`, `object`, `identity`, etc)
`desc`
    Describes the service
`owner_id`
    References the user who owns the service

`credentials`
-------------

`id`
    Auto-incremented primary key
`user_id`
    References the user who owns the credential.
`tenant_id`
    References the tenant upon which the credential can be used for.
`types`
    Indicates the type of credential (e.g. `Password`, `APIKey`, `EC2`).
`key`
    TODO: Key of what?
`secret`
    TODO: Secret of what?

`tokens`
--------

`id`
    Auto-incremented primary key
`user_id`
    References the user who owns the token
`tenant_id`
    References the tenant the token is scoped to
`expires`
    Indicates the expiration date of the token, after which the token can no longer be validated successfully.

`endpoints`
-----------

Tenant-specific endpoints. The `tenant_id` which appears here replaces the
`%tenant_id%` placeholder in the specified endpoint template.

`tenant_id`
    References the tenant this endpoint applies to.

`endpoint_template_id`
    The endpoint template to appear in the user's service catalog.

`endpoint_templates`
--------------------

A multi-purpose model for the service catalog which can be:

- Provided to users of a specific tenants via `endpoints`, when `is_global` is false.
- Provided to all users as-is, when `is_global` is true.

`id`
    Primary key (TODO: Why is this not auto-incremented?)
`region`
    The physical region the endpoint is located within
`service_id`
    TODO: References the service which owns the endpoints?
`public_url`
    Appears in the service catalog [#first]_.

    Represents an endpoint available on the public Internet.
`admin_url`
    Appears in the service catalog [#first]_.

    Users of this endpoint must have an Admin or ServiceAdmin role.
`internal_url`
    Appears in the service catalog [#first]_.

    Represents an endpoint on an internal, unmetered network.
`enabled`
    If false, this endpoint template will not appear in the service catalog.
`is_global`
    If true, this endpoint can not be mapped to tenant-specific endpoints, and `%tenant_id%` will not be substituted in endpoint URL's. Additionally, this endpoint will appear for all users.
`version_id`
    TODO: Version ID of what?
`version_list`
    TODO: Version list of what?
`version_info`
    TODO: Version info of what?

.. [#first] `%tenant_id%` may be replaced by actual tenant references, depending on the value of `is_global` and the existence of a corresponding `endpoints` record.
