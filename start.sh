#!/usr/bin/bash

uwsgi  --module "keystone.server.wsgi:initialize_public_application()" -s :5001 -b 65535
