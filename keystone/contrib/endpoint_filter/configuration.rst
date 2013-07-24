Instructions to enable the OS-EP-FILTER Extension.

To enable the endpoint filter extension the following keystone.conf changes must be applied:

1) Add the extension catalog handler for SQL
Please add the following line in the [catalog] section of the config file:
driver = keystone.contrib.endpoint_filter.backends.catalog_sql.OS_EP_Filter_Catalog
NOTE: This line is in addition to the catalog driver that you are currently using.

2) Enable the extension
[os_ep_filter]
# create associations between project and endpoints in order to provide
# a tailored catalog for project-scoped token requests.
# driver = keystone.contrib.endpoint_filter.backends.sql.EndpointFilter
enabled = True

3) OPTIONAL: enable and customize the backend driver
driver = keystone.contrib.endpoint_filter.backends.{your backend}.EndpointFilter
