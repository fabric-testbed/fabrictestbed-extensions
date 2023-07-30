FablibManager
-------------

.. automodule:: fablib
   :members:

.. autoclass:: fablib.FablibManager
   :members:


Slice
-----

.. automodule:: slice
   :members:

.. autoclass:: slice.Slice
   :members:


``Node``
----------------

.. automodule:: node

.. autoclass:: node.Node


``Component``
----------------------------

.. automodule:: component
   :members:

.. autoclass:: component.Component
   :members:


.. automodule:: interface

``Interface``
----------------------


.. autoclass:: interface.Interface

  .. automethod:: __str__

  .. automethod:: toJson

  .. automethod:: toDict

  .. automethod:: show

  .. automethod:: get_mac

  .. automethod:: get_device_name

  .. automethod:: get_os_interface

  .. automethod:: get_physical_os_interface

  .. automethod:: ip_addr_add

  .. automethod:: ip_addr_del

  .. automethod:: ip_link_up

  .. automethod:: ip_link_down

  .. automethod:: set_vlan

  .. automethod:: get_bandwidth

  .. automethod:: get_vlan

  .. automethod:: get_reservation_state

  .. automethod:: get_name

  .. automethod:: get_component

  .. automethod:: get_model

  .. automethod:: get_site

  .. automethod:: get_slice

  .. automethod:: get_node

  .. automethod:: get_network

  .. automethod:: get_ip_link

  .. automethod::  get_ip_addr

  .. automethod::  get_ips

  .. automethod:: get_numa_node

  .. automethod:: un_manage_interface

.. automodule:: network_service


``NetworkService``
------------------------------------

.. autoclass:: network_service.NetworkService

  .. automethod:: __str__

  .. automethod:: toJson

  .. automethod:: toDict

  .. automethod:: show

  .. automethod:: get_fim_network_service

  .. automethod:: get_slice

  .. automethod:: get_name

  .. automethod:: get_interfaces

  .. automethod:: get_interface

  .. automethod:: has_interface

  .. automethod:: get_layer

  .. automethod:: get_type

  .. automethod:: get_error_message

  .. automethod:: get_gateway

  .. automethod:: get_available_ips

  .. automethod:: get_subnet

  .. automethod:: get_reservation_id

  .. automethod:: get_reservation_state

  .. automethod:: get_public_ips

.. automodule:: resources

``Resources``
------------------------------------

.. autoclass:: resources.Resources

  .. automethod:: __str__

  .. automethod:: show_site

  .. automethod:: get_site_names

  .. automethod:: get_component_capacity

  .. automethod:: get_component_allocated

  .. automethod:: get_component_available

  .. automethod:: get_location_lat_long

  .. automethod:: get_location_postal

  .. automethod:: get_host_capacity

  .. automethod:: get_cpu_capacity

  .. automethod:: get_core_capacity

  .. automethod:: get_core_allocated

  .. automethod:: get_core_available

  .. automethod:: get_ram_capacity

  .. automethod:: get_ram_allocated

  .. automethod:: get_ram_available

  .. automethod:: get_disk_capacity

  .. automethod:: get_disk_allocated

  .. automethod:: get_disk_available

  .. automethod:: update

  .. automethod:: get_site_list

  .. automethod:: get_link_list
