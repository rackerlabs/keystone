#!/usr/bin/env bash

# Generate sample configuration for your project.

oslo-config-generator --namespace oslo.messaging --namespace oslo.db \
  --namespace keystone > etc/keystone.conf.sample
