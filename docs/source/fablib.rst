:orphan:

`fabrictestbed_extensions/fablib` stuff.

.. automodule:: fablib

``FablibManager``
----------------------

.. autoclass:: fablib.FablibManager

   .. automethod:: set_log_level

   .. automethod:: get_log_level

   .. automethod:: get_log_file

   .. automethod:: get_log_file

   .. automethod:: get_image_names

   .. automethod:: get_site_names

   .. automethod:: list_sites

   .. automethod:: show_site

   .. automethod:: get_resources

   .. automethod:: get_random_site

   .. automethod:: get_random_sites

   .. automethod:: get_default_slice_key

   .. automethod:: get_config

   .. automethod:: get_default_slice_public_key

   .. automethod:: get_default_slice_public_key_file

   .. automethod:: get_default_slice_private_key_file

   .. automethod:: get_default_slice_private_key_passphrase

   .. automethod:: get_credmgr_host

   .. automethod:: get_orchestrator_host

   .. automethod:: get_fabric_token

   .. automethod:: get_bastion_username

   .. automethod:: get_bastion_key_filename

   .. automethod:: get_bastion_public_addr

   .. automethod:: get_bastion_private_ipv4_addr

   .. automethod:: get_bastion_private_ipv6_addr

   .. automethod:: set_slice_manager

   .. automethod:: get_slice_manager

   .. automethod:: new_slice

   .. automethod:: get_available_resources

   .. automethod:: get_slices

   .. automethod:: get_slice

   .. automethod:: delete_slice

   .. automethod:: delete_all

   .. automethod:: get_log_level

.. automodule:: slice

``Slice``
--------------

.. autoclass:: slice.Slice

  .. automethod:: __str__

  .. automethod:: save

  .. automethod:: load

  .. automethod:: list_nodes

  .. automethod:: list_interfaces

  .. automethod:: new_slice

  .. automethod:: get_fim_topology

  .. automethod:: update

  .. automethod:: get_slice_public_key

  .. automethod:: get_private_key_passphrase

  .. automethod:: get_slice_public_key_file

  .. automethod:: get_slice_private_key_file

  .. automethod:: isStable

  .. automethod:: get_state

  .. automethod:: get_name

  .. automethod:: get_slice_id

  .. automethod:: get_lease_end

  .. automethod:: add_l2network

  .. automethod:: add_l3network

  .. automethod:: add_node

  .. automethod:: get_object_by_reservation

  .. automethod:: get_error_messages

  .. automethod:: get_notices

  .. automethod:: get_components

  .. automethod:: get_nodes

  .. automethod:: get_node

  .. automethod:: get_interfaces

  .. automethod:: get_interface

  .. automethod:: get_networks

  .. automethod:: get_network

  .. automethod:: get_l2networks

  .. automethod:: get_l2network

  .. automethod:: get_l3networks

  .. automethod:: get_l3network

  .. automethod:: add_facility_port

  .. automethod:: delete

  .. automethod:: renew

  .. automethod:: wait

  .. automethod:: wait_ssh

  .. automethod:: test_ssh

  .. automethod:: post_boot_config

  .. automethod:: submit


``Node``
----------------

.. automodule:: node

.. autoclass:: node.Node

 .. automethod:: __str__

 .. automethod:: set_capacities

 .. automethod:: set_instance_type

 .. automethod:: set_image

 .. automethod:: set_host

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

 .. automethod:: clear_all_ifaces

 .. automethod:: remove_all_vlan_os_interfaces

 .. automethod:: remove_vlan_os_interface

 .. automethod:: add_vlan_os_interface

 .. automethod:: ping_test


.. automodule:: component

``Component``
----------------------------

.. autoclass:: component.Component

  .. automethod:: __str__

  .. automethod:: list_interfaces




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



.. automodule:: interface

``Interface``
----------------------


.. autoclass:: interface.Interface

  .. automethod:: __str__

  .. automethod:: get_mac

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


.. automodule:: network_service


``NetworkService``
------------------------------------

.. autoclass:: network_service.NetworkService

  .. automethod:: __str__

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
