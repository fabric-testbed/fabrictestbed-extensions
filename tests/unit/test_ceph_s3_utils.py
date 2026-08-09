#!/usr/bin/env python3
"""Unit tests for the Ceph S3 (RGW) helpers."""
import os
import stat
from unittest import mock

import pytest

from fabrictestbed_extensions.utils.ceph_s3_utils import (
    CephS3Credentials,
    CephS3Error,
)

CLUSTER_INFO = {
    "data": [
        {"cluster": "east", "fsid": "f1",
         "s3_endpoints": ["http://10.133.124.2:8080", "http://10.137.252.2:8080"]},
        {"cluster": "west", "fsid": "f2", "s3_endpoints": []},
    ]
}


def _mgr(**overrides):
    m = mock.MagicMock()
    m.list_cluster_info.return_value = CLUSTER_INFO
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _patch(mgr):
    return mock.patch(
        "fabrictestbed_extensions.utils.ceph_s3_utils.CephManagerClient",
        return_value=mgr,
    )


# --------------------------------------------------------------------------
# endpoint discovery
# --------------------------------------------------------------------------

def test_list_s3_endpoints():
    with _patch(_mgr()):
        eps = CephS3Credentials.list_s3_endpoints(base_url="https://x", cluster="east")
    assert eps == ["http://10.133.124.2:8080", "http://10.137.252.2:8080"]


def test_unknown_cluster_lists_what_is_available():
    with _patch(_mgr()), pytest.raises(CephS3Error, match="Unknown cluster"):
        CephS3Credentials.list_s3_endpoints(base_url="https://x", cluster="nope")


def test_cluster_without_endpoints_is_an_error():
    """An older Ceph Manager returns no s3_endpoints; say so clearly."""
    with _patch(_mgr()), pytest.raises(CephS3Error, match="no S3 endpoints"):
        CephS3Credentials.list_s3_endpoints(base_url="https://x", cluster="west")


# --------------------------------------------------------------------------
# credentials
# --------------------------------------------------------------------------

def test_existing_readable_key_is_reused():
    mgr = _mgr()
    mgr.list_s3_user_keys.return_value = [
        {"access_key": "AK1", "secret_key": "SK1"},
    ]
    with _patch(mgr):
        creds = CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="alice_1")
    assert (creds["access_key"], creds["secret_key"]) == ("AK1", "SK1")
    assert creds["endpoint"] == "http://10.133.124.2:8080"
    mgr.create_s3_user_key.assert_not_called()


def test_key_is_minted_when_secret_is_withheld():
    """The list endpoint withholds secrets, so a new key must be created."""
    mgr = _mgr()
    mgr.list_s3_user_keys.return_value = [{"access_key": "AK1", "secret_key": None}]
    mgr.create_s3_user_key.return_value = {"access_key": "AK2", "secret_key": "SK2"}
    with _patch(mgr):
        creds = CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="alice_1")
    assert (creds["access_key"], creds["secret_key"]) == ("AK2", "SK2")
    mgr.create_s3_user_key.assert_called_once()


def test_no_mint_when_disallowed():
    mgr = _mgr()
    mgr.list_s3_user_keys.return_value = [{"access_key": "AK1", "secret_key": None}]
    with _patch(mgr), pytest.raises(CephS3Error, match="create_if_missing"):
        CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="alice_1",
            create_if_missing=False)
    mgr.create_s3_user_key.assert_not_called()


def test_missing_user_still_mints():
    """A user that does not exist yet surfaces as a failed list; minting covers it."""
    mgr = _mgr()
    mgr.list_s3_user_keys.side_effect = RuntimeError("404 NoSuchUser")
    mgr.create_s3_user_key.return_value = {"access_key": "AK3", "secret_key": "SK3"}
    with _patch(mgr):
        creds = CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="bob_2")
    assert creds["access_key"] == "AK3"


def test_bad_mint_response_is_an_error():
    mgr = _mgr()
    mgr.list_s3_user_keys.return_value = []
    mgr.create_s3_user_key.return_value = {"access_key": "AK", "secret_key": None}
    with _patch(mgr), pytest.raises(CephS3Error, match="did not return a new keypair"):
        CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="bob_2")


# --------------------------------------------------------------------------
# client config artifacts
# --------------------------------------------------------------------------

@pytest.fixture
def creds():
    return {
        "cluster": "east", "uid": "alice_1",
        "access_key": "AKIAEXAMPLE", "secret_key": "s3cr3t",
        "endpoint": "http://10.133.124.2:8080",
        "endpoints": ["http://10.133.124.2:8080"],
        "region": "us-east-1",
    }


def test_write_client_config_produces_all_artifacts(creds, tmp_path):
    files = CephS3Credentials.write_client_config(creds, out_base=tmp_path)
    assert set(files) == {"aws_credentials", "aws_config", "s3cfg", "env.sh", "README.md"}
    for path in files.values():
        assert os.path.exists(path)


def test_secret_bearing_files_are_not_world_readable(creds, tmp_path):
    files = CephS3Credentials.write_client_config(creds, out_base=tmp_path)
    for name in ("aws_credentials", "s3cfg", "env.sh"):
        mode = stat.S_IMODE(os.stat(files[name]).st_mode)
        assert mode == 0o600, f"{name} is mode {oct(mode)}, should be 0600"


def test_client_config_contents(creds, tmp_path):
    files = CephS3Credentials.write_client_config(creds, out_base=tmp_path)
    aws = open(files["aws_credentials"]).read()
    assert "aws_access_key_id = AKIAEXAMPLE" in aws
    assert "aws_secret_access_key = s3cr3t" in aws

    cfg = open(files["aws_config"]).read()
    assert "endpoint_url = http://10.133.124.2:8080" in cfg
    assert "addressing_style = path" in cfg      # RGW needs path style

    s3cfg = open(files["s3cfg"]).read()
    assert "host_base = 10.133.124.2:8080" in s3cfg
    assert "use_https = False" in s3cfg

    env = open(files["env.sh"]).read()
    assert "export AWS_ACCESS_KEY_ID=AKIAEXAMPLE" in env


def test_https_endpoint_sets_use_https(tmp_path, creds):
    creds = dict(creds, endpoint="https://s3.example.org")
    files = CephS3Credentials.write_client_config(creds, out_base=tmp_path)
    assert "use_https = True" in open(files["s3cfg"]).read()


# --------------------------------------------------------------------------
# bucket listing (Ceph Manager API — no S3 client involved)
# --------------------------------------------------------------------------

def test_list_buckets_returns_the_data_array():
    mgr = _mgr()
    mgr.list_s3_buckets.return_value = {
        "data": [
            {"name": "b1", "owner": "alice_1", "num_objects": 3},
            {"name": "b2", "owner": "alice_1", "num_objects": 0},
        ],
        "total": 2,
    }
    with _patch(mgr):
        out = CephS3Credentials.list_buckets(
            base_url="https://x", cluster="east", uid="alice_1")
    assert [b["name"] for b in out] == ["b1", "b2"]
    mgr.list_s3_buckets.assert_called_once_with("east", uid="alice_1")


def test_list_buckets_tolerates_an_empty_or_odd_response():
    for payload in ({"data": []}, {}, None, {"data": [None, "junk"]}):
        mgr = _mgr()
        mgr.list_s3_buckets.return_value = payload
        with _patch(mgr):
            assert CephS3Credentials.list_buckets(
                base_url="https://x", cluster="east") == []


def test_credentials_reuse_an_existing_key_via_include_secret():
    """
    The secret must be requested explicitly, otherwise the service withholds it
    and every call would mint a new keypair.
    """
    mgr = _mgr()
    mgr.list_s3_user_keys.return_value = [{"access_key": "AK1", "secret_key": "SK1"}]
    with _patch(mgr):
        CephS3Credentials.get_credentials(
            base_url="https://x", cluster="east", uid="alice_1")
    mgr.list_s3_user_keys.assert_called_once_with("east", "alice_1", include_secret=True)
    mgr.create_s3_user_key.assert_not_called()


def test_module_does_not_import_boto3():
    """FABlib must not gain a boto3 dependency; S3 data transfer is out of scope."""
    import fabrictestbed_extensions.utils.ceph_s3_utils as mod
    src = open(mod.__file__).read()
    assert "\nimport boto3" not in src
    assert "\n    import boto3" not in src
    assert not hasattr(mod, "CephS3"), "the boto3 data-plane class should be gone"
