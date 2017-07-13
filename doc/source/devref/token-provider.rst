..
      Copyright 2011-2012 OpenStack Foundation
      All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

==========================
Configuring token provider
==========================

OpenStack Identity supports customizable token providers. This is specified
in the ``[token]`` section of the configuration file. The token provider
controls the token construction, validation, and revocation operations.

You can register your own token provider by configuring the following property:

.. note::

   More commonly, you can use this option to change the token provider to one
   of the ones built in. Alternatively, you can use it to configure your own
   token provider.

* ``provider`` - token provider driver.
  Defaults to ``uuid``.
  Implemented by :class:`keystone.token.providers.uuid.Provider`. This is the
  entry point for the token provider in the ``keystone.token.provider``
  namespace.
