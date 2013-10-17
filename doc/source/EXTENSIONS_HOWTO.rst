Keystone Extensions Development Guide
=====================================


General
-------

This Extension Development Guide provides some mocked code to use as an
Extension code base in the `keystone/contrib/example` folder.


- All Extensions must be created in the `keystone/contrib` folder.
- The new Extension code must be contained in a new folder under `contrib`.
- Whenever possible an Extension should follow the following structure
  convention:


      keystone
          \\\  contrib
                \\\  my_extension
                         \\\  backends             (optional)

                         \\\  migrate_repo         (optional)

                         \\\  __init__.py          (mandatory)

                         \\\  configuration.rst    (mandatory)

                         \\\  core.py              (mandatory)

                         \\\  controllers.py       (mandatory for API Extension)

                         \\\  routers.py           (mandatory for API Extension)


- If the Extension implements an API Extension the `controllers.py` and
  `routers.py` must be present and correctly handle the API Extension requests
  and responses.
- If the Extension implements backends a `backends` folder should exist.
  Backends are defined to store data persistently and can use a variety of
  technologies. Please see the Backends section in this document for more info.
- If the Extension adds data structures a `migrate_repo` folder should exist.
- If configuration changes are required/introduced in the `keystone.conf.sample`
  file, these should be kept disabled as default and have their own element.
- If configuration changes are required/introduced in the `keystone-paste.ini`,
  the new filter must be declared.
- If the configuration is listening to core notifications, the events list and
  corresponding callbacks must be declared in the ``core.py`` file.


`keystone.conf.sample` File
---------------------------

In the case an Extension needs to change the `keystone.conf.sample` file, it
must follow the config file conventions and introduce a dedicated entry.

Example::

    [example]
    driver = keystone.contrib.example.backends.sql.mySQLClass


    [myOtherExtension]
    extension_flag = False


The Extension parameters expressed should be commented out since, by default,
extensions are disabled.

Example::

    [example]
    #driver = keystone.contrib.example.backends.sql.mySQLClass


    [myOtherExtension]
    #extension_flag = False


In case the Extension is overriding or re-implementing an existing portion of
Keystone the required change should be commented in the `configuration.rst` but
not placed in the `keystone.conf.sample` file to avoid unecessary confusion.

In case the Extension requires to be notified of changes in the main Keystone
entities, the Extension notifier must be activated.

Example::

    # === Notification Options ===

    # Notifications can be sent when users or projects are created, updated or
    ...
    # Keystone Extensions Notification Driver (not enabled by default)
    notification_driver = keystone.common.extensions_notifier


`keystone-paste.ini` File
--------------------------

In the case an Extension is augmenting a pipeline introducing a new `filter`
and/or APIs in the `OS` namespace, a corresponding `filter:` section is
necessary to be introduced in the `keystone-paste.ini` file.
The Extension should declare the filter factory constructor in the `ini` file.

Example::

    [filter:example]
    paste.filter_factory = keystone.contrib.example.routers:ExampleRouter.
    factory

The `filter` must not be placed in the `pipeline` and treated as optional.
How to add the extension in the pipeline should be specified in detail in the
`configuration.rst` file.


Package Constructor File
------------------------

The `__init__.py` file represents the package constructor. Extension needs to
import what is necessary from the `core.py` module.

Example:

.. code:: python

   from keystone.contrib.example.core import *


Core
----

The `core.py` file represents the main module defining the data structure and
interface. In the `Model View Control` (MVC) model it represents the `Model`
part and it delegates to the `Backends` the data layer implementation.

In case the `core.py` file contains a `Manager` and a `Driver` it must provide
the dependency injections for the `Controllers` and/or other modules using the
`Manager`. A good practice is to call the dependency `extension_name_api`.


Example:

.. code:: python

    @dependency.provider('example_api')
    class Manager(manager.Manager):


Routers
-------

`routers.py` have the objective of routing the HTTP requests and direct them to
the right method within the `Controllers`. Extension routers are extending the
`wsgi.ExtensionRouter`.


Example:

.. code:: python

    from keystone.common import wsgi
    from keystone.contrib.example import controllers


    class ExampleRouter(wsgi.ExtensionRouter):

        PATH_PREFIX = '/OS-EXAMPLE'

        def add_routes(self, mapper):
            example_controller = controllers.ExampleV3Controller()
            mapper.connect(self.PATH_PREFIX + '/example',
                           controller=example_controller,
                           action='do_something',
                           conditions=dict(method=['GET']))
        ...



Controllers
-----------

`controllers.py` have the objective of handing requests and implement the
Extension logic. Controllers are consumers of 'Managers' API and must have all
the dependency injections required. `Controllers` are extending the
`V3Controller` class.


Example:

.. code:: python

    @dependency.requires('identity_api', 'example_api')
    class ExampleV3Controller(controller.V3Controller):
    ...


Backends
--------

The `backends` folder provides the model implementations for the different
backends supported by the Extension.
The folder structure must be the following:


    keystone
        \\\  contrib
              \\\  my_extension
                       \\\  backends
                              \\\   __init__.py       (required)

                              \\\   sql.py            (optional)

                              \\\   kvs.py            (optional)


If a SQL backend is provided, in the `sql.py` backend implementation it is
mandatory to define the new table(s) that the Extension introduces and the
attributes they are composed of.


For more information on Backends please consult the Keystone Architecture
documentation:
(http://docs.openstack.org/developer/keystone/architecture.html)


Example:

.. code:: python

    class ExampleSQLBackend(sql.ModelBase, sql.DictBase):
        """example table description."""
        __tablename__ = 'example_table'
        attributes = ['id', 'type', 'extra']

        example_id = sql.Column(sql.String(64),
                                primary_key=True,
                                nullable=False)
        ...



Migrate Repository
------------------

In case the Extension is adding data structures, these must be stored in
separate tables and must not be included in the `migrate_repo` of the core
Keystone. Please refere to the 'migrate.cfg' file to configure the Extension
repository.


In order to create the Extension tables and its attributes, a db_sync command
must be executed.


Example::

     ./bin/keystone-manage db_sync --extension example


Event Notifications
-------------------

Extensions can subscribe to Keystone (Identity) event notifications.
Extensions must provide the list of events of interest and the corresponding
callbacks. Events are issued upon successful creation, modification, and
deletion of the following Keystone resources:

* ``group``
* ``project``
* ``role``
* ``user``

The extension's ``Manager`` class must contain the
``notification_subscriptions`` attribute. It is a dictionary listing as keys
those events that are of interest and the values should be the respective
callbacks. Notification subscription registration is done via the
dependency injection mechanism. During dependency provider registration, the
``dependency.provider`` decorator looks for the ``notification_subscriptions``
class attribute. If it exist the notification callbacks are registered
accordingly. Needless to say, in order to subscript event notifications, the
extension's ``Manager`` class must also be a dependency provider.

Example:

.. code:: python
    @dependency.provider('example_api')
    class ExampleManager(manager.Manager):
        """Example Manager.

        See :mod:`keystone.common.manager.Manager` for more details on
        how this dynamically calls the backend.

        """

        notification_subscriptions = {}

        def __init__(self):
            # Register the notification callback for when projects are
            # deleted. This information is used when the @dependency.provider
            # decorator acts on the class.
            self.notification_subscriptions.setdefault('deleted', {})
            self.notification_subscriptions['deleted'].setdefault(
                'project', [])
            self.notification_subscriptions['deleted']['project'].append(
                self.project_deleted_notification)
            super(ExampleManager, self).__init__(
                'keystone.contrib.example.core.ExampleDriver')

        def project_deleted_notification(self, context, message):
            # cleanup data related to the deleted project here

Callbacks must be expecting the following parameters:

* ``context`` - the session context
* ``message`` - the notification message

Example:

.. code:: python
      def project_deleted_notification(self, context, message)


Events in Keystone follow this format: ``identity.<resource>.<operation>``
where the operations are ``created``, ``updated`` and ``deleted``. Please refer
to the :doc:`event_notifications` for more information on notifications.
