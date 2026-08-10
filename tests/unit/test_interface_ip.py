"""Unit tests for interface IP address parsing helpers."""

import pytest

from fabrictestbed_extensions.fablib.interface import parse_ip_addr_json

# Sample data mimicking `ip -j addr show` output
SAMPLE_ADDR_ENTRY = {
    "ifindex": 3,
    "ifname": "ens7",
    "flags": ["BROADCAST", "MULTICAST", "UP", "LOWER_UP"],
    "mtu": 9000,
    "qdisc": "mq",
    "operstate": "UP",
    "group": "default",
    "txqlen": 1000,
    "link_type": "ether",
    "address": "aa:bb:cc:dd:ee:ff",
    "broadcast": "ff:ff:ff:ff:ff:ff",
    "addr_info": [
        {
            "family": "inet",
            "local": "10.20.30.40",
            "prefixlen": 24,
            "broadcast": "10.20.30.255",
            "scope": "global",
            "label": "ens7",
            "valid_life_time": 4294967295,
            "preferred_life_time": 4294967295,
        },
        {
            "family": "inet6",
            "local": "fe80::a8bb:ccff:fedd:eeff",
            "prefixlen": 64,
            "scope": "link",
            "valid_life_time": 4294967295,
            "preferred_life_time": 4294967295,
        },
    ],
}


class TestParseIpAddrJson:
    """Tests for parse_ip_addr_json()."""

    def test_all_addresses(self):
        result = parse_ip_addr_json(SAMPLE_ADDR_ENTRY)
        assert result == ["10.20.30.40", "fe80::a8bb:ccff:fedd:eeff"]

    def test_filter_inet(self):
        result = parse_ip_addr_json(SAMPLE_ADDR_ENTRY, family="inet")
        assert result == ["10.20.30.40"]

    def test_filter_inet6(self):
        result = parse_ip_addr_json(SAMPLE_ADDR_ENTRY, family="inet6")
        assert result == ["fe80::a8bb:ccff:fedd:eeff"]

    def test_empty_addr_info(self):
        entry = {"ifname": "lo", "addr_info": []}
        result = parse_ip_addr_json(entry)
        assert result == []

    def test_missing_addr_info_key(self):
        entry = {"ifname": "lo"}
        result = parse_ip_addr_json(entry)
        assert result == []

    def test_no_matching_family(self):
        entry = {
            "ifname": "ens7",
            "addr_info": [
                {"family": "inet", "local": "192.168.1.1"},
            ],
        }
        result = parse_ip_addr_json(entry, family="inet6")
        assert result == []

    def test_multiple_ipv4_addresses(self):
        entry = {
            "ifname": "ens7",
            "addr_info": [
                {"family": "inet", "local": "10.0.0.1"},
                {"family": "inet", "local": "10.0.0.2"},
            ],
        }
        result = parse_ip_addr_json(entry, family="inet")
        assert result == ["10.0.0.1", "10.0.0.2"]

    def test_addr_info_with_missing_local(self):
        entry = {
            "ifname": "ens7",
            "addr_info": [
                {"family": "inet"},
                {"family": "inet", "local": "10.0.0.1"},
            ],
        }
        result = parse_ip_addr_json(entry)
        assert result == ["10.0.0.1"]
