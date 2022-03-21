:orphan:

`fabrictestbed_extensions/fablib` stuff.


``AbcFabLIB``
------------------------------

.. autoclass:: abc_fablib.AbcFabLIB

   .. automethod:: __init__




``Interface``
----------------------


.. autoclass:: interface.Interface

   .. automethod:: __init__

   .. automethod:: get_os_interface

   .. automethod:: get_mac

   .. automethod:: get_physical_os_interface

   .. automethod:: config_vlan_iface

   .. automethod:: set_ip

   .. automethod:: set_vlan

   .. automethod:: get_fim_interface

   .. automethod:: get_bandwidth

   .. automethod:: get_vlan

   .. automethod:: get_name

   .. automethod:: get_component

   .. automethod:: get_model

   .. automethod:: get_site

   .. automethod:: get_slice

   .. automethod:: get_node

   .. automethod:: get_network

``NetworkService``
------------------------------------


.. autoclass:: NetworkService

   .. automethod:: calculate_l2_nstype

   .. automethod:: validate_nstype

   .. automethod:: new_l2network

   .. automethod:: new_network_service

   .. automethod:: get_l2network_services

   .. automethod:: get_l2network_service

   .. automethod:: __init__

   .. automethod:: get_slice

   .. automethod:: get_fim_network_service

   .. automethod:: get_name

   .. automethod:: get_interfaces

   .. automethod:: get_interface

   .. automethod:: has_interface

   .. automethod:: find_nic_mapping

   .. automethod:: flush_dataplane_ips

   .. automethod:: flush_all_dataplane_ips

``Node``
----------------


.. autoclass:: Node

   .. automethod:: __init__

   .. automethod:: new_node

   .. automethod:: get_node

   .. automethod:: get_fim_node

   .. automethod:: set_capacities

   .. automethod:: set_instance_type

   .. automethod:: set_username

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

   .. automethod:: validIPAddress

   .. automethod:: execute

   .. automethod:: upload_file

   .. automethod:: download_file

   .. automethod:: test_ssh

   .. automethod:: wait_for_ssh

   .. automethod:: get_management_os_interface

   .. automethod:: get_dataplane_os_interfaces

   .. automethod:: flush_all_os_interfaces

   .. automethod:: flush_os_interface

   .. automethod:: set_ip_os_interface

   .. automethod:: clear_all_ifaces

   .. automethod:: remove_all_vlan_os_interfaces

   .. automethod:: save_data

   .. automethod:: load_data

   .. automethod:: remove_vlan_os_interface

   .. automethod:: add_vlan_os_interface

   .. automethod:: ping_test


``Slice``
--------------

.. autoclass:: Slice

   .. automethod:: __init__

   .. automethod:: new_slice

   .. automethod:: get_slice

   .. automethod:: get_fim_topology

   .. automethod:: update_slice

   .. automethod:: update_topology

   .. automethod:: update

   .. automethod:: get_slice_public_key

   .. automethod:: get_private_key_passphrase

   .. automethod:: get_slice_public_key_file

   .. automethod:: get_slice_private_key_file

   .. automethod:: get_state

   .. automethod:: get_name

   .. automethod:: get_slice_id

   .. automethod:: get_lease_end

   .. automethod:: add_l2network

   .. automethod:: add_node

   .. automethod:: get_nodes

   .. automethod:: get_node

   .. automethod:: get_interfaces

   .. automethod:: get_interface

   .. automethod:: get_l2networks

   .. automethod:: get_l2network

   .. automethod:: delete

   .. automethod:: renew

   .. automethod:: wait

   .. automethod:: get_interface_map

   .. automethod:: post_boot_config

   .. automethod:: load_config

   .. automethod:: load_interface_map

   .. automethod:: build_interface_map

   .. automethod:: submit

 ``Component``
 ----------------------------

 .. autoclass:: component.Component

    .. automethod:: __init__

    .. automethod:: calculate_name

    .. automethod:: new_component

    .. automethod:: get_interfaces

    .. automethod:: get_fim_component

    .. automethod:: get_slice

    .. automethod:: get_node

    .. automethod:: get_site

    .. automethod:: get_name

    .. automethod:: get_details

    .. automethod:: get_disk

    .. automethod:: get_unit

    .. automethod:: get_pci_addr

    .. automethod:: get_model

    .. automethod:: get_fim_model

    .. automethod:: get_type

    .. automethod:: configure_nvme
