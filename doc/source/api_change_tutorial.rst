..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

API Change Tutorial
===================

This document will guide you through the process of proposing and submitting
and API change in keystone.

Prerequisites
-------------

In order to follow this tutorial, it is assumed that you have read our
`developer guide`_ and `architecture`_ documents.

.. _`developer guide`: http://docs.openstack.org/developer/keystone/developing.html
.. _`architecture`: http://docs.openstack.org/developer/keystone/architecture.html

Proposing a change
------------------

You need to submit a specification against the `keystone-specs`_ repository and
bring it up to discussion with the `keystone core team`_ for agreement.

.. _`keystone-specs`: https://git.openstack.org/cgit/openstack/keystone-specs/
.. _`keystone core team`: https://review.openstack.org/#/admin/groups/9,members

Create
~~~~~~

#. git clone https://git.openstack.org/openstack/keystone-specs ;
#. Use the provided `template`_ ;
#. Push to gerrit for review ;
#. Propose agenda items to the `keystone meeting`_, and make sure someone
   who understands the subject can attend the meeting to answer questions.

.. _`template`: https://git.openstack.org/cgit/openstack/keystone-specs/tree/specs/template.rst
.. _`keystone meeting`: https://wiki.openstack.org/wiki/Meetings/KeystoneMeeting

Agreement
~~~~~~~~~

The `keystone core team`_ will evaluate the specification and vote on accepting
it or not. If accepted, the proposal will be targeted to a release; otherwise,
the specification will be abandoned.

As soon as there is an agreement on the specification, the change may start
rolling out.

Implementing a change
---------------------

In this section, let's assume that a specification proposing the addition of a
`description` field to roles was accepted. In the next subsections, you will
find a detailed explanation on the needed code changes to the keystone code to
implementh such change.

Architectural Recapitulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As you saw in the `architecture`_ document, there are four logical levels of
code at which a sucessful request calls: router, controller, manager and
driver.

For the role backend, they can be found in the directory keystone/assignment,
in the following paths, respectively: routers.py, controllers.py, core.py and
role_backends/sql.py (currently only the SQL driver is supported).

Changing the Model
~~~~~~~~~~~~~~~~~~

First, you need to change the role model to include the description attribute.
Go to keystone/assignment/role_backends/sql.py and update it like::

    class RoleTable(sql.ModelBase, sql.DictBase):

        attributes = ['id', 'name', 'domain_id', 'description']
        description = sql.Column(sql.String(255), nullable=True)
        ...

Now, when keystone runs, the table will be created with the new attribute.
However, what about existing deployments which already have the role table
created ? You need to migrate their database schema!

The directory keystone/common/sql/migrate_repo/versions owns all the migrations
since keystone day 1. Create a new file there with the next migration number.
For example, if the lastest migration number there is `101`, create yours as
`102_add_role_description.py`, which looks like::

      def upgrade(migrate_engine):
          meta = sql.MetaData()
          meta.bind = migrate_engine

          role_table = sql.Table('role', meta, autoload=True)
          description = sql.Column('description', sql.String(255),
                                   nullable=True)
          role_table.create_column(description)

Do not forget to add tests for your migration at
`keystone/tests/unit/test_sql_upgrade.py`, you may take other tests as example
and learn how to develop yours. In this case, you would need to upgrade to
check the role table contains the description column after migration.

Changing the Manager
~~~~~~~~~~~~~~~~~~~~

Managers handle the business logic. Keystone provides the basic CRUD for role
entities, that means that the role manager simply calls the driver with the
arguments received from the controller, and then returns the driver's result
back to controller. Additionally, it handles the cache management.

Thus, there is no manager change needed to make it able to operate role
entities with the new `description` attribute.

However, you should add tests for the role CRUD operations with the new
attribute to `keystone/tests/unit/assignment/test_core.py`.

Changing the Controller and Router
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The controller is in charge of calling the appropriate manager call and wrap
responses into HTTP format. It passes and accepts all the attributes to and
from the manager. Thus, there is no change needed at the controller level.

In addition, as role entities are passed in the request body to keystone calls,
the role routes do not need to be changed; i.e the routes still are::

      POST /v3/roles
      GET /v3/roles/{id}
      HEAD /v3/roles/{id}
      PATCH /v3/roles/{id}
      DELETE /v3/roles/{id}

Conclusion
----------

At this point, keystone role entities contain a `description` attribute. In
order to make it happen, you have learned how the keystone architecture is,
what is the responsability of each layer, how database migrations occur and the
way entities are represented into tables.

The pattern of the change made in this tutorial applies to other keystone
subsystems as well, such as `resource` and `identity`.