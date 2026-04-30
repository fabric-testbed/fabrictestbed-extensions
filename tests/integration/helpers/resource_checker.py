"""Resource availability checking utilities for integration tests.

Provides functions to check whether specific resource requirements
can be satisfied before a test begins, enabling graceful skip behavior
instead of test failures caused by resource exhaustion.
"""

from dataclasses import dataclass
from typing import List, Optional

import pytest


@dataclass
class ResourceRequirement:
    """Describes the minimum resources needed for a test.

    :param cores: minimum CPU cores
    :param ram: minimum RAM in GB
    :param disk: minimum disk in GB
    :param sites: number of distinct sites needed
    :param shared_nic: NIC_Basic count
    :param smartnic_cx6: ConnectX-6 SmartNIC count
    :param gpu_t4: Tesla T4 GPU count
    :param fpga_u280: Xilinx U280 FPGA count
    :param nvme: NVMe drive count
    """

    cores: int = 2
    ram: int = 8
    disk: int = 10
    sites: int = 1
    shared_nic: int = 0
    smartnic_cx6: int = 0
    smartnic_cx5: int = 0
    gpu_t4: int = 0
    gpu_rtx6000: int = 0
    gpu_a30: int = 0
    gpu_a40: int = 0
    fpga_u280: int = 0
    nvme: int = 0


# Map ResourceRequirement field names to list_sites dict keys
_FIELD_TO_SITE_KEY = {
    "cores": "cores_available",
    "ram": "ram_available",
    "disk": "disk_available",
    "shared_nic": "nic_basic_available",
    "smartnic_cx6": "nic_connectx_6_available",
    "smartnic_cx5": "nic_connectx_5_available",
    "gpu_t4": "tesla_t4_available",
    "gpu_rtx6000": "rtx6000_available",
    "gpu_a30": "a30_available",
    "gpu_a40": "a40_available",
    "fpga_u280": "fpga_u280_available",
    "nvme": "nvme_available",
}


def find_sites_for_requirement(
    fablib,
    requirement: ResourceRequirement,
) -> Optional[List[str]]:
    """Find sites satisfying the given resource requirement.

    :param fablib: FablibManager instance
    :param requirement: resource requirements to satisfy
    :return: list of site names, or None if unsatisfiable
    :rtype: Optional[List[str]]
    """
    sites = fablib.list_sites(output="list", quiet=True)

    def site_matches(site_data: dict) -> bool:
        if site_data.get("state") != "Active":
            return False
        if site_data.get("hosts", 0) <= 0:
            return False
        for field_name, site_key in _FIELD_TO_SITE_KEY.items():
            required = getattr(requirement, field_name, 0)
            if required > 0:
                available = site_data.get(site_key, 0) or 0
                if available < required:
                    return False
        return True

    matching = [s["name"] for s in sites if site_matches(s)]

    if len(matching) < requirement.sites:
        return None

    return matching[: requirement.sites]


def find_site_with_component(fablib, component_key: str, min_available: int = 1):
    """Find a site with a specific component available.

    :param fablib: FablibManager instance
    :param component_key: availability dict key (e.g. "tesla_t4_available")
    :param min_available: minimum units needed
    :return: site name, or None if not found
    :rtype: Optional[str]
    """
    sites = fablib.list_sites(output="list", quiet=True)
    candidates = [
        s
        for s in sites
        if s.get("state") == "Active"
        and s.get("hosts", 0) > 0
        and (s.get(component_key, 0) or 0) >= min_available
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda s: s.get(component_key, 0) or 0, reverse=True)
    return candidates[0]["name"]


def skip_if_unavailable(fablib, requirement: ResourceRequirement):
    """Skip the test if resources are unavailable.

    :param fablib: FablibManager instance
    :param requirement: resource requirements to check
    :return: list of matching site names
    :rtype: List[str]
    """
    result = find_sites_for_requirement(fablib, requirement)
    if result is None:
        needs = []
        for field_name in _FIELD_TO_SITE_KEY:
            val = getattr(requirement, field_name, 0)
            if val > 0:
                needs.append(f"{field_name}={val}")
        pytest.skip(
            f"Resources unavailable: need {requirement.sites} site(s) "
            f"with {', '.join(needs)}"
        )
    return result
