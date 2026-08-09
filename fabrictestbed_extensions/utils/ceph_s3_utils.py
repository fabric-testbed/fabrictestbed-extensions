#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2025 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
# Author: Komal Thareja (kthare10@renci.org)
"""
S3 (Ceph RGW) helpers for FABlib.

Scope is deliberately narrow: **discovery and credentials only**. This module
talks to the Ceph Manager API to find a cluster's S3 endpoint, to list the
buckets a user owns, and to hand back access keys — then gets out of the way.

Object upload/download is intentionally *not* implemented here. Doing so would
pull boto3 into FABlib's dependency tree for every user, whether or not they
touch S3. Use the credentials from :meth:`CephS3Credentials.get_credentials`
with any standard S3 client instead (aws-cli, s3cmd, boto3, rclone);
:meth:`CephS3Credentials.write_client_config` writes ready-to-use config for the
common ones.

The S3 ``uid`` is the user's bastion login, the same identity used for CephFS
subvolumes.

RGW endpoints are FABNet addresses, so S3 is reachable from FABRIC slices (and
anywhere with FABNet routing), not from the open internet.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fabric_ceph_client.fabric_ceph_client import CephManagerClient

DEFAULT_REGION = "us-east-1"


class CephS3Error(RuntimeError):
    """Raised when an S3 helper cannot complete a request."""


def _client(base_url: str, token: Optional[str], token_file: Optional[str],
            verify: bool) -> CephManagerClient:
    return CephManagerClient(
        base_url=base_url, token=token, token_file=token_file, verify=verify
    )


class CephS3Credentials:
    """
    Discovery and credential retrieval via the Ceph Manager API.

    Everything here is a control-plane call requiring a FABRIC token; none of it
    moves object data.
    """

    @staticmethod
    def list_s3_endpoints(
        *,
        base_url: str,
        cluster: str,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        verify: bool = True,
    ) -> List[str]:
        """
        Return the RGW S3 endpoint URLs for ``cluster``, in preference order.

        :raises CephS3Error: if the cluster is unknown or advertises no endpoint.
        """
        c = _client(base_url, token, token_file, verify)
        info = c.list_cluster_info()
        items = (info or {}).get("data", []) if isinstance(info, dict) else []
        for item in items:
            if isinstance(item, dict) and item.get("cluster") == cluster:
                endpoints = item.get("s3_endpoints") or []
                if not endpoints:
                    raise CephS3Error(
                        f"Cluster '{cluster}' advertises no S3 endpoints. The Ceph "
                        f"Manager may predate S3 support."
                    )
                return list(endpoints)
        known = [i.get("cluster") for i in items if isinstance(i, dict)]
        raise CephS3Error(f"Unknown cluster '{cluster}'. Available: {known}")

    @staticmethod
    def get_credentials(
        *,
        base_url: str,
        cluster: str,
        uid: str,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        verify: bool = True,
        create_if_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Return usable S3 credentials for ``uid`` on ``cluster``.

        An existing keypair is reused when one can be read back. Only when the
        user has no key at all (or none whose secret is retrievable) is a new
        one minted, so repeated calls do not accumulate credentials.

        :return: ``{cluster, uid, access_key, secret_key, endpoint, endpoints, region}``
        :raises CephS3Error: when no usable credential can be obtained.
        """
        c = _client(base_url, token, token_file, verify)
        endpoints = CephS3Credentials.list_s3_endpoints(
            base_url=base_url, cluster=cluster, token=token,
            token_file=token_file, verify=verify,
        )

        # Ask for the secret so an existing keypair can be reused. Without this
        # the service withholds secrets and every call would mint a new key,
        # accumulating credentials without bound.
        access_key = secret_key = None
        try:
            existing = c.list_s3_user_keys(cluster, uid, include_secret=True)
            for k in existing or []:
                if isinstance(k, dict) and k.get("access_key") and k.get("secret_key"):
                    access_key, secret_key = k["access_key"], k["secret_key"]
                    break
        except Exception:
            # Most often the S3 user does not exist yet; minting handles it.
            existing = []

        if not secret_key:
            if not create_if_missing:
                raise CephS3Error(
                    f"No readable secret key for '{uid}' on '{cluster}'. Re-run "
                    f"with create_if_missing=True to mint one."
                )
            created = c.create_s3_user_key(cluster, uid, generate=True)
            if not isinstance(created, dict) or not created.get("secret_key"):
                raise CephS3Error(
                    f"Ceph Manager did not return a new keypair for '{uid}' on "
                    f"'{cluster}': {created!r}"
                )
            access_key, secret_key = created["access_key"], created["secret_key"]

        return {
            "cluster": cluster,
            "uid": uid,
            "access_key": access_key,
            "secret_key": secret_key,
            "endpoint": endpoints[0],
            "endpoints": endpoints,
            "region": DEFAULT_REGION,
        }

    @staticmethod
    def list_buckets(
        *,
        base_url: str,
        cluster: str,
        uid: Optional[str] = None,
        token: Optional[str] = None,
        token_file: Optional[str] = None,
        verify: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List S3 buckets via the Ceph Manager API (no S3 client required).

        The service scopes the result by identity: a non-operator always sees
        only the buckets they own, whatever ``uid`` is passed.

        :return: ``[{name, owner, num_objects, size_kb, versioning, ...}, ...]``
        """
        c = _client(base_url, token, token_file, verify)
        resp = c.list_s3_buckets(cluster, uid=uid)
        data = (resp or {}).get("data", []) if isinstance(resp, dict) else []
        return [b for b in data if isinstance(b, dict)]

    @staticmethod
    def write_client_config(
        creds: Dict[str, Any],
        out_base: Path | str = "./ceph-s3-artifacts",
    ) -> Dict[str, str]:
        """
        Write ready-to-use config for common S3 clients.

        Produces an AWS credentials/config pair, an ``.s3cfg`` for s3cmd, an
        ``env.sh``, and a short README. Files containing secrets are written
        ``0600``.

        :return: mapping of artifact name → path written.
        """
        cluster = creds["cluster"]
        base = Path(out_base).expanduser().resolve() / cluster
        base.mkdir(parents=True, exist_ok=True)

        endpoint = creds["endpoint"]
        host = endpoint.split("://", 1)[-1]
        use_https = endpoint.startswith("https://")
        written: Dict[str, str] = {}

        def _write(name: str, text: str, secret: bool = False) -> None:
            p = base / name
            p.write_text(text)
            os.chmod(p, 0o600 if secret else 0o644)
            written[name] = str(p)

        _write(
            "aws_credentials",
            f"[fabric-{cluster}]\n"
            f"aws_access_key_id = {creds['access_key']}\n"
            f"aws_secret_access_key = {creds['secret_key']}\n",
            secret=True,
        )
        _write(
            "aws_config",
            f"[profile fabric-{cluster}]\n"
            f"region = {creds['region']}\n"
            f"s3 =\n"
            f"    endpoint_url = {endpoint}\n"
            f"    addressing_style = path\n",
        )
        _write(
            "s3cfg",
            f"[default]\n"
            f"access_key = {creds['access_key']}\n"
            f"secret_key = {creds['secret_key']}\n"
            f"host_base = {host}\n"
            f"host_bucket = {host}/%(bucket)\n"
            f"use_https = {'True' if use_https else 'False'}\n"
            f"signature_v2 = False\n",
            secret=True,
        )
        _write(
            "env.sh",
            f"# source this file\n"
            f"export AWS_ACCESS_KEY_ID={creds['access_key']}\n"
            f"export AWS_SECRET_ACCESS_KEY={creds['secret_key']}\n"
            f"export AWS_DEFAULT_REGION={creds['region']}\n"
            f"export AWS_ENDPOINT_URL={endpoint}\n",
            secret=True,
        )
        _write(
            "README.md",
            f"# FABRIC S3 credentials — {cluster}\n\n"
            f"S3 user (uid): `{creds['uid']}`\n"
            f"Endpoint: `{endpoint}`\n\n"
            f"Endpoints are FABNet addresses — reachable from a FABRIC slice, not "
            f"from the open internet.\n\n"
            f"## aws-cli\n\n"
            f"```bash\n"
            f"export AWS_SHARED_CREDENTIALS_FILE={base}/aws_credentials\n"
            f"export AWS_CONFIG_FILE={base}/aws_config\n"
            f"aws --profile fabric-{cluster} --endpoint-url {endpoint} s3 ls\n"
            f"aws --profile fabric-{cluster} --endpoint-url {endpoint} "
            f"s3 cp ./file s3://<bucket>/file\n"
            f"```\n\n"
            f"## s3cmd\n\n"
            f"```bash\n"
            f"s3cmd -c {base}/s3cfg ls\n"
            f"```\n\n"
            f"## boto3\n\n"
            f"```python\n"
            f"import boto3\n"
            f"s3 = boto3.client('s3', endpoint_url='{endpoint}',\n"
            f"                  aws_access_key_id='...', aws_secret_access_key='...',\n"
            f"                  region_name='{creds['region']}')\n"
            f"```\n",
        )
        return written
