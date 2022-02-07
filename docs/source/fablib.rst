fablib
------
`fabrictestbed_extensions/fablib` stuff.

.. automodule:: abc_fablib

``abc_fablib``
===============

.. autoclass:: abc_fablib.AbcFabLIB

   .. automethod:: __init__

.. automodule:: component

``component``
==============

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

.. autoclass:: component.Disk

   .. automethod:: __init__

.. autoclass:: component.NIC

   .. automethod:: __init__

.. autoclass:: component.GPU

   .. automethod:: __init__

.. automodule:: fablib

``fablib``
===========

.. automodule:: fablib

.. autoclass:: fablib.fablib

   .. automethod:: __init__

   .. automethod:: build_slice_manager

   .. automethod:: init_fablib

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

   .. automethod:: create_slice_manager

   .. automethod:: new_slice

   .. automethod:: get_site_advertisment

   .. automethod:: get_available_resources

   .. automethod:: get_slices

   .. automethod:: get_slice

   .. automethod:: delete_slice

   .. automethod:: delete_all

``interface``
===========

.. automodule:: interface

.. autoclass:: Interface

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

``network_service``
==================

.. automodule:: network_service

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
