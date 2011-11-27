================
Extensions
================

Keystone uses extensions to add capability to the API beyond those of the specification.

  
Enabling/Disabling extensions.
------------------------------
  Keystone conf file has a property called extensions.This property holds the list of supported extensions.If you want to
  add/remove an extension from being supported, add/remove the extension key from this property.
  
  
Adding additional extensions.
------------------------------
 Extensions are subject to an approval process.
 If you want your extension available to the public, submit and get your blueprint approved prior to coding. 

To add a new extension, these are the steps involved.

1. Decide a short hand name for extension ie extension key.

2. Decide whether the extension enhances Admin API, Service API or both.

3. Add a folder with the name we have already decided @ /contrib/extensions/{admin or service} based on which API we are enhancing.

4. Add static extension json(name it as extension.json) and extension xml (name it as extension.xml) info to the new extension folder.Refer `Service Guide <https://github.com/openstack/keystone/blob/master/keystone/content/admin/identityadminguide.pdf?raw=true>`_
`Sample extension XML <https://github.com/openstack/keystone/blob/master/keystone/content/common/samples/extension.json>`_
`Sample extension JSON <https://github.com/openstack/keystone/blob/master/keystone/content/common/samples/extension.xml>`_ to know the content structure.

5. If your extension is adding additional methods override the base class 'BaseExtensionHandler' call it 'ExtensionHandler' and add your methods.

6. If your extension modifies existing calls existing code need to be modified to support the extension.

7. Add your extension name to the list of supported extensions in the keystone conf file. 
   
 
   