.. automodule:: fablib

FablibManager
-------------

.. autoclass:: fablib.FablibManager
   :members:


Slice
-----

.. automodule:: slice
.. autoclass:: slice.Slice
   :members:


``Node``
----------------

.. automodule:: node

.. autoclass:: node.Node

 .. automethod:: __str__

 .. automethod:: toJson

 .. automethod:: toDict

 .. automethod:: show

 .. automethod:: list_components

 .. automethod:: list_interfaces

 .. automethod:: list_networks

 .. automethod:: get_fim_node

 .. automethod:: set_capacities

 .. automethod:: set_instance_type

 .. automethod:: set_image

 .. automethod:: set_host

 .. automethod:: set_site

 .. automethod:: get_slice

 .. automethod:: get_name

 .. automethod:: get_cores

 .. automethod:: get_ram

 .. automethod:: get_disk

 .. automethod:: get_image

 .. automethod:: get_image_type

 .. automethod:: get_host

 .. automethod:: get_site

 .. automethod:: get_management_ip

 .. automethod:: get_reservation_id

 .. automethod:: get_reservation_state

 .. automethod:: get_error_message

 .. automethod:: get_interfaces

 .. automethod:: get_interface

 .. automethod:: get_username

 .. automethod:: get_public_key

 .. automethod:: get_public_key_file

 .. automethod:: get_private_key

 .. automethod:: get_private_key_file

 .. automethod:: get_private_key_passphrase

 .. automethod:: add_component

 .. automethod:: get_components

 .. automethod:: get_component

 .. automethod:: get_ssh_command

 .. automethod:: execute

 .. automethod:: execute_thread

 .. automethod:: upload_file

 .. automethod:: upload_file_thread

 .. automethod:: upload_directory

 .. automethod:: upload_directory_thread

 .. automethod:: download_file

 .. automethod:: download_file_thread

 .. automethod:: download_directory

 .. automethod:: download_directory_thread

 .. automethod:: test_ssh

 .. automethod:: get_management_os_interface

 .. automethod:: get_dataplane_os_interfaces

 .. automethod:: flush_all_os_interfaces

 .. automethod:: flush_os_interface

 .. automethod:: ip_route_add

 .. automethod:: ip_route_del

 .. automethod:: ip_addr_add

 .. automethod:: ip_addr_del

 .. automethod:: ip_link_up

 .. automethod:: ip_link_down

 .. automethod:: network_manager_stop

 .. automethod:: network_manager_start

 .. automethod:: get_ip_routes

 .. automethod:: get_ip_addrs

 .. automethod:: clear_all_ifaces

 .. automethod:: remove_all_vlan_os_interfaces

 .. automethod:: remove_vlan_os_interface

 .. automethod:: add_vlan_os_interface

 .. automethod:: ping_test

 .. automethod:: get_storage

 .. automethod:: add_storage

 .. automethod:: un_manage_interface


.. automodule:: component

``Component``
----------------------------

.. autoclass:: component.Component

  .. automethod:: __str__

  .. automethod:: toJson

  .. automethod:: toDict

  .. automethod:: show


  .. automethod:: list_interfaces

  .. automethod:: get_fim_component



  .. automethod:: get_interfaces


  .. automethod:: get_slice

  .. automethod:: get_node

  .. automethod:: get_site

  .. automethod:: get_name

  .. automethod:: get_disk

  .. automethod:: get_unit

  .. automethod:: get_pci_addr

  .. automethod:: get_model

  .. automethod:: get_reservation_id

  .. automethod:: get_reservation_state

  .. automethod:: get_error_message

  .. automethod:: configure_nvme

  .. automethod:: get_numa_node



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
