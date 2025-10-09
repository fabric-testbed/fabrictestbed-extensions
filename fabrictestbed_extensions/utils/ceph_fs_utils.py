# CephFsUtils.py
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from fabric_ceph_client import CephManagerClient
except Exception:
    from fabric_ceph_client.fabric_ceph_client import CephManagerClient


class CephFsUtils:
    """
    Build CephFS client artifacts (conf, keyring, secret, mount script) for a cluster/user.

    The utility parses a CephX keyring, extracts the base64 secret and MDS caps,
    writes a minimal client bundle on disk, and generates an idempotent mount script.
    The script installs files under ``/etc/ceph`` using **cluster-prefixed** names and
    mounts all paths discovered in the MDS capabilities. It first attempts a kernel
    mount with ``fs=<fsname>`` and falls back to ``mds_namespace=<fsname>`` on ``EINVAL``.

    Bundle layout (under ``<out_base>/<cluster>/``):
      * ``ceph.conf``
      * ``ceph.client.<user>.keyring``
      * ``ceph.client.<user>.secret``
      * ``mount_<user>.sh``

    Mount points:
      * For each ``(fsname, path)`` pair in the user's MDS caps, the script mounts:
        ``<mount_root_default>/<cluster>/<user>/<slug(path)>``.

    :param cluster: Logical cluster name (e.g., ``"asia"``). Must be non-empty.
    :type cluster: str
    :param ceph_conf_text: Minimal Ceph configuration text for the cluster.
    :type ceph_conf_text: str
    :param keyring_blob: Keyring content as plain text, or a JSON-encoded string of that text.
    :type keyring_blob: str
    :param out_base: Output directory for artifacts. Defaults to current directory.
    :type out_base: pathlib.Path | str, optional
    :param mount_root_default: Root under which per-user mountpoints are created.
    :type mount_root_default: str, optional

    :raises ValueError: If ``cluster`` is empty.
    """

    def __init__(
        self,
        cluster: str,
        ceph_conf_text: str,
        keyring_blob: str,
        *,
        out_base: Path | str = ".",
        mount_root_default: str = "/mnt/cephfs",
    ):
        self.cluster = str(cluster).strip()
        if not self.cluster:
            raise ValueError("cluster must be a non-empty string")
        self.ceph_conf_text = ceph_conf_text
        self.keyring_blob = keyring_blob
        self.out_base = Path(out_base).resolve()
        self.mount_root_default = mount_root_default

        # Filled by parse()
        self.entity: Optional[str] = None  # client.foo
        self.user_only: Optional[str] = None  # foo
        self.secret: Optional[str] = None  # base64
        self.fs_paths: List[Tuple[str, str]] = []  # (fsname, path)

    # ---------------- Public API ----------------

    def build(self) -> Dict[str, Any]:
        """
        Parse inputs, write artifacts, and return a summary.

        :return: Summary dictionary with keys:
                 ``cluster_dir``, ``ceph_conf``, ``secret_file``, ``keyring_file``,
                 ``mount_script``, ``entity``, ``user``, and ``mounts`` (a list of
                 objects having ``fsname``, ``path``, and ``mount_point``).
        :rtype: Dict[str, Any]
        :raises ValueError: If the keyring cannot be parsed or contains no MDS cap paths.
        """
        text = self._unescape_if_json(self.keyring_blob)
        self._parse_keyring(text)

        cluster_dir = self.out_base / self.cluster
        cluster_dir.mkdir(parents=True, exist_ok=True)

        conf_path = self._write_conf(cluster_dir)
        secret_path, keyring_path = self._write_secrets(cluster_dir, text)
        script_path = self._write_script(cluster_dir)

        return {
            "cluster_dir": str(cluster_dir),
            "ceph_conf": str(conf_path),
            "secret_file": str(secret_path),
            "keyring_file": str(keyring_path),
            "mount_script": str(script_path),
            "entity": self.entity,
            "user": self.user_only,
            "mounts": [
                {
                    "fsname": fs,
                    "path": p,
                    "mount_point": f"{self.mount_root_default}/{self.cluster}/{self.user_only}/{self._slug_from_path(p)}",
                }
                for fs, p in self.fs_paths
            ],
        }

    # ---------------- API helpers ----------------

    @staticmethod
    def list_clusters_from_api(
        *,
        base_url: str,
        token_file: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = True,
    ) -> List[str]:
        """
        List cluster names available from the Ceph Manager API.

        :param base_url: Ceph Manager API base URL.
        :type base_url: str
        :param token_file: Path to a token file (mutually exclusive with ``token``).
        :type token_file: str | None, optional
        :param token: Raw token string (mutually exclusive with ``token_file``).
        :type token: str | None, optional
        :param verify: Whether to verify TLS certificates.
        :type verify: bool, optional
        :return: List of cluster names.
        :rtype: List[str]
        """
        c = CephManagerClient(
            base_url=base_url, token=token, token_file=token_file, verify=verify
        )
        info = c.list_cluster_info()
        items = (info or {}).get("data", []) if isinstance(info, dict) else []
        return [
            i.get("cluster") for i in items if isinstance(i, dict) and i.get("cluster")
        ]

    @staticmethod
    def build_for_user_from_api(
        *,
        user_entity: str,
        base_url: str,
        cluster: str,
        token_file: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = True,
        out_base: Path | str = "./ceph-artifacts",
        mount_root_default: str = "/mnt/cephfs",
    ) -> Dict[str, Any]:
        """
        Build artifacts for a specific CephX entity using the Manager API.

        This fetches a minimal ``ceph.conf`` for ``cluster`` and exports the keyring
        for ``user_entity`` (e.g., ``client.alice``). It then constructs a
        :class:`CephFsUtils` and returns the result of :meth:`build`.

        :param user_entity: CephX entity, e.g., ``client.alice``.
        :type user_entity: str
        :param base_url: Ceph Manager API base URL.
        :type base_url: str
        :param cluster: Cluster name to target.
        :type cluster: str
        :param token_file: Path to a token file (mutually exclusive with ``token``).
        :type token_file: str | None, optional
        :param token: Raw token string (mutually exclusive with ``token_file``).
        :type token: str | None, optional
        :param verify: Whether to verify TLS certificates.
        :type verify: bool, optional
        :param out_base: Output directory root.
        :type out_base: pathlib.Path | str, optional
        :param mount_root_default: Mount root used by the generated script.
        :type mount_root_default: str, optional
        :return: Summary dictionary from :meth:`build`.
        :rtype: Dict[str, Any]
        :raises ValueError: If the target cluster is not found or the user keyring is missing.
        """
        c = CephManagerClient(
            base_url=base_url, token=token, token_file=token_file, verify=verify
        )

        # ceph.conf (minimal) for the cluster
        info = c.list_cluster_info()
        items = (info or {}).get("data", []) if isinstance(info, dict) else []
        entry = next(
            (x for x in items if isinstance(x, dict) and x.get("cluster") == cluster),
            None,
        )
        if not entry:
            raise ValueError(f"Cluster '{cluster}' not found")
        ceph_conf_text = entry.get("ceph_conf_minimal")
        if not isinstance(ceph_conf_text, str) or not ceph_conf_text.strip():
            raise ValueError(f"Cluster '{cluster}' is missing ceph_conf_minimal")

        # Keyring for user on that cluster
        export = c.export_users(cluster=cluster, entities=[user_entity])
        key_blob = (
            ((export or {}).get("clusters", {}) or {}).get(cluster, {}).get(user_entity)
        )
        if not key_blob:
            raise ValueError(f"No keyring for {user_entity} on cluster '{cluster}'")

        return CephFsUtils(
            cluster=cluster,
            ceph_conf_text=ceph_conf_text,
            keyring_blob=key_blob,
            out_base=out_base,
            mount_root_default=mount_root_default,
        ).build()

    @staticmethod
    def build_for_login_from_api(
        *,
        login: str,
        base_url: str,
        cluster: str,
        token_file: Optional[str] = None,
        token: Optional[str] = None,
        verify: bool = True,
        out_base: Path | str = "./ceph-artifacts",
        mount_root_default: str = "/mnt/cephfs",
        prefix: str = "client.",
    ) -> Dict[str, Any]:
        """
        Build artifacts for a bastion login, assuming ``client.<login>`` entity.

        :param login: Bastion login name (e.g., ``kthare10_0011904101``).
        :type login: str
        :param base_url: Ceph Manager API base URL.
        :type base_url: str
        :param cluster: Cluster name to target.
        :type cluster: str
        :param token_file: Path to a token file (mutually exclusive with ``token``).
        :type token_file: str | None, optional
        :param token: Raw token string (mutually exclusive with ``token_file``).
        :type token: str | None, optional
        :param verify: Whether to verify TLS certificates.
        :type verify: bool, optional
        :param out_base: Output directory root.
        :type out_base: pathlib.Path | str, optional
        :param mount_root_default: Mount root used by the generated script.
        :type mount_root_default: str, optional
        :param prefix: Entity prefix to prepend to ``login`` (defaults to ``"client."``).
        :type prefix: str, optional
        :return: Summary dictionary from :meth:`build`.
        :rtype: Dict[str, Any]
        """
        entity = f"{prefix}{login}" if prefix else login
        return CephFsUtils.build_for_user_from_api(
            user_entity=entity,
            base_url=base_url,
            cluster=cluster,
            token_file=token_file,
            token=token,
            verify=verify,
            out_base=out_base,
            mount_root_default=mount_root_default,
        )

    # ---------------- Parsing ----------------

    @staticmethod
    def _unescape_if_json(s: str) -> str:
        """
        Return the string unchanged unless it's a JSON string literal.

        :param s: Possibly JSON-encoded string.
        :type s: str
        :return: Decoded string if JSON; otherwise the original string.
        :rtype: str
        """
        try:
            return json.loads(s)
        except Exception:
            return s

    @staticmethod
    def _require_regex(regex: str, text: str, desc: str, flags=0) -> re.Match:
        """
        Search with regex and raise if not found.

        :param regex: Pattern to search.
        :type regex: str
        :param text: Input text.
        :type text: str
        :param desc: Human-friendly description used in error messages.
        :type desc: str
        :param flags: Optional regex flags.
        :type flags: int
        :return: The first regex match.
        :rtype: re.Match
        :raises ValueError: If the pattern is not found.
        """
        m = re.search(regex, text, flags)
        if not m:
            raise ValueError(f"Could not find {desc} in keyring")
        return m

    def _parse_keyring(self, text: str) -> None:
        """
        Parse entity, secret, and MDS caps out of keyring text.

        Expected features:

          * ``[client.<name>]`` stanza
          * ``key = <base64>`` line
          * ``caps mds = "allow rw fsname=FS path=/foo, ..."`` (one or more)

        If exactly one ``fsname`` appears among clauses, it is used as the default
        for clauses missing an explicit ``fsname=...``. Duplicate ``(fsname, path)``
        pairs are de-duplicated in order of appearance.

        :param text: Keyring text.
        :type text: str
        :raises ValueError: If required pieces cannot be parsed, or no MDS cap paths exist.
        """
        # [client.USER]
        m_ent = self._require_regex(
            r"\[(client\.[^\]]+)\]", text, "[client.<name>] stanza"
        )
        self.entity = m_ent.group(1)
        self.user_only = self.entity.split(".", 1)[1]

        # key = <secret>
        m_key = self._require_regex(
            r"^\s*key\s*=\s*([A-Za-z0-9+/=]+)\s*$", text, "'key =' line", flags=re.M
        )
        self.secret = m_key.group(1)

        # caps mds = "allow rw fsname=FS path=/foo, allow rw fsname=FS path=/bar"
        m_caps = re.search(r'caps\s+mds\s*=\s*"([^"]+)"', text)
        paths: List[Tuple[str, str]] = []
        if m_caps:
            body = m_caps.group(1)
            clauses = [c.strip() for c in re.split(r"\s*,\s*", body) if c.strip()]
            seen_fs: List[str] = []
            for cl in clauses:
                mfs = re.search(r"fsname=([^,\s]+)", cl)
                if mfs:
                    fsn = mfs.group(1)
                    if fsn not in seen_fs:
                        seen_fs.append(fsn)

            def default_fs() -> Optional[str]:
                return seen_fs[0] if len(seen_fs) == 1 else None

            for cl in clauses:
                mfs = re.search(r"fsname=([^,\s]+)", cl)
                mp = re.search(r"path=([^,\s]+)", cl)
                if not mp:
                    continue
                fsn = mfs.group(1) if mfs else default_fs()
                if not fsn:
                    raise ValueError(
                        "Found MDS cap without fsname=... and cannot infer default FS."
                    )
                pth = mp.group(1)
                paths.append((fsn, pth))

            # de-dup preserve order
            uniq: List[Tuple[str, str]] = []
            seen: set[Tuple[str, str]] = set()
            for fp in paths:
                if fp not in seen:
                    seen.add(fp)
                    uniq.append(fp)
            paths = uniq

        if not paths:
            raise ValueError("No fsname/path entries found in MDS caps")

        self.fs_paths = paths

    # ---------------- Writers ----------------

    def _write_conf(self, cluster_dir: Path) -> Path:
        """
        Write ``ceph.conf`` into the cluster output directory.

        :param cluster_dir: Output cluster directory.
        :type cluster_dir: pathlib.Path
        :return: Path to the written ``ceph.conf`` file.
        :rtype: pathlib.Path
        """
        conf_path = cluster_dir / "ceph.conf"
        conf_path.write_text(self.ceph_conf_text, encoding="utf-8")
        return conf_path

    def _write_secrets(self, cluster_dir: Path, keyring_text: str) -> Tuple[Path, Path]:
        """
        Write secret and keyring files (mode 600) to the output directory.

        :param cluster_dir: Output cluster directory.
        :type cluster_dir: pathlib.Path
        :param keyring_text: Original keyring text (for reference).
        :type keyring_text: str
        :return: Tuple ``(secret_path, keyring_path)``.
        :rtype: Tuple[pathlib.Path, pathlib.Path]
        """
        # secret file (use by kernel mount via secretfile=)
        secret_path = cluster_dir / f"ceph.client.{self.user_only}.secret"
        secret_path.write_text(self.secret + "\n", encoding="utf-8")
        os.chmod(secret_path, 0o600)

        # full keyring (for reference / admin tools)
        keyring_path = cluster_dir / f"ceph.client.{self.user_only}.keyring"
        keyring_path.write_text(keyring_text, encoding="utf-8")
        os.chmod(keyring_path, 0o600)

        return secret_path, keyring_path

    def _write_script(self, cluster_dir: Path) -> Path:
        """
        Generate an idempotent mount script for all discovered MDS cap paths.

        The script:
          * Installs cluster-scoped files under ``/etc/ceph`` with cluster prefixes.
          * Creates per-user mount directories.
          * Tries kernel mount with ``fs=`` first, falls back to ``mds_namespace=``.
          * Skips a path if it is already mounted.

        :param cluster_dir: Output cluster directory.
        :type cluster_dir: pathlib.Path
        :return: Path to the generated shell script (mode 0750).
        :rtype: pathlib.Path
        """
        script_name = f"mount_{self.user_only}.sh"
        script_path = cluster_dir / script_name

        # Build mount blocks with fs= and fallback to mds_namespace=
        blocks: List[str] = []
        for fsname, path in self.fs_paths:
            slug = self._slug_from_path(path)
            mnt = f"$MNT_BASE/$CLUSTER/$USER_NAME/{slug}"

            blk = f"""
    # --- {fsname}:{path} ---
    echo "Preparing mountpoint: {mnt}"
    sudo mkdir -p "{mnt}"

    # If already mounted, skip
    if mountpoint -q "{mnt}"; then
      current_src="$(findmnt -n -o SOURCE --target "{mnt}" 2>/dev/null || true)"
      echo "Already mounted at {mnt} (SOURCE=${{current_src:-unknown}}). Skipping."
    else
      # Set perms on empty dir
      sudo chown "${{owner_uid}}:${{owner_gid}}" "{mnt}" || true
      sudo chmod 755 "{mnt}" || true

      echo "Mounting (fs=) fs={fsname} path={path} -> {mnt}"
      set +e
      sudo mount -t ceph ":{path}" "{mnt}" -o name="$USER_NAME",secretfile="$SECRET_TGT",conf="$CONF_TGT",fs="{fsname}",_netdev,noatime
      rc=$?
      set -e
      if [[ $rc -eq 22 ]]; then
        echo "fs= not accepted (EINVAL). Retrying with mds_namespace={fsname} ..."
        sudo mount -t ceph ":{path}" "{mnt}" -o name="$USER_NAME",secretfile="$SECRET_TGT",conf="$CONF_TGT",mds_namespace="{fsname}",_netdev,noatime
        rc=$?
      fi

      if [[ $rc -ne 0 ]]; then
        echo "ERROR: mount failed with rc=$rc for {mnt}"
        exit $rc
      fi

      # Fix ownership of the mountpoint root (best-effort)
      sudo chown -R "${{owner_uid}}:${{owner_gid}}" "{mnt}" || true
    fi
    """
            blocks.append(blk)

        script = f"""#!/usr/bin/env bash
    set -euo pipefail

    # Installs /etc/ceph/<cluster>.conf, /etc/ceph/<cluster>.client.<user>.keyring and .secret,
    # fixes mount dir permissions, and mounts all paths discovered in your MDS caps.

    here="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    CLUSTER="{self.cluster}"
    ENTITY="{self.entity}"
    USER_NAME="{self.user_only}"
    MNT_BASE="${{MNT_BASE:-{self.mount_root_default}}}"

    echo "Using cluster: $CLUSTER"
    echo "Bundle dir:   $here"
    echo "Mount base:   $MNT_BASE"

    # Cluster-scoped targets in /etc/ceph
    if [[ "$CLUSTER" == "ceph" || -z "$CLUSTER" ]]; then
      CONF_TGT="/etc/ceph/ceph.conf"
      KEYRING_TGT="/etc/ceph/ceph.client.$USER_NAME.keyring"
      SECRET_TGT="/etc/ceph/ceph.client.$USER_NAME.secret"
    else
      CONF_TGT="/etc/ceph/${{CLUSTER}}.conf"
      KEYRING_TGT="/etc/ceph/${{CLUSTER}}.client.$USER_NAME.keyring"
      SECRET_TGT="/etc/ceph/${{CLUSTER}}.client.$USER_NAME.secret"
    fi

    # Helper: copy if missing or changed
    copy_if_changed() {{
      local src="$1" dst="$2" mode="$3"
      if [[ ! -f "$dst" ]] || ! cmp -s "$src" "$dst"; then
        sudo install -m "$mode" -D "$src" "$dst"
      fi
    }}

    # Ensure /etc/ceph has the right files (idempotent)
    sudo mkdir -p /etc/ceph
    copy_if_changed "$here/ceph.conf" "$CONF_TGT" 644
    copy_if_changed "$here/ceph.client.$USER_NAME.keyring" "$KEYRING_TGT" 600
    copy_if_changed "$here/ceph.client.$USER_NAME.secret" "$SECRET_TGT" 600

    # Determine non-root owner for mount dirs
    owner_uid="${{SUDO_UID:-}}"
    owner_gid="${{SUDO_GID:-}}"
    if [[ -z "$owner_uid" || -z "$owner_gid" ]]; then
      owner_uid="$(stat -c %u "$here")"
      owner_gid="$(stat -c %g "$here")"
    fi

    # User base
    sudo mkdir -p "$MNT_BASE/$CLUSTER/$USER_NAME"
    if ! mountpoint -q "$MNT_BASE/$CLUSTER/$USER_NAME"; then
      sudo chown "${{owner_uid}}:${{owner_gid}}" "$MNT_BASE/$CLUSTER/$USER_NAME" || true
      sudo chmod 755 "$MNT_BASE/$CLUSTER/$USER_NAME" || true
    fi

    {"".join(blocks)}

    echo "All mounts attempted."
    echo "To unmount:"
    echo "  sudo umount -l $MNT_BASE/$CLUSTER/$USER_NAME/*"
    """
        script_path.write_text(script, encoding="utf-8")
        os.chmod(script_path, 0o750)
        return script_path

    # ---------------- Utils ----------------

    @staticmethod
    def _slug_from_path(p: str) -> str:
        """
        Convert a CephFS path into a safe slug for directory naming.

        :param p: Path like ``/volumes/_nogroup/user/subvol-uuid``.
        :type p: str
        :return: A filesystem-safe slug (alphanumerics and ``._-``), or ``"root"`` for ``"/"``.
        :rtype: str
        """
        p = p.strip().lstrip("/")
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", p)
        return slug or "root"


# ------------ Sphinx-friendly helpers ------------


def list_ceph_clusters(
    *,
    base_url: str,
    token_file: Optional[str] = None,
    token: Optional[str] = None,
    verify: bool = True,
) -> List[str]:
    """
    Return cluster names from the Ceph Manager API.

    Thin wrapper around :meth:`CephFsUtils.list_clusters_from_api`.

    :param base_url: Ceph Manager API base URL.
    :type base_url: str
    :param token_file: Path to token file.
    :type token_file: str | None, optional
    :param token: Raw token string.
    :type token: str | None, optional
    :param verify: Whether to verify TLS certificates.
    :type verify: bool, optional
    :return: List of cluster names.
    :rtype: List[str]
    """
    return CephFsUtils.list_clusters_from_api(
        base_url=base_url, token_file=token_file, token=token, verify=verify
    )


def build_ceph_bundle_for_user(
    *,
    user_entity: str,
    base_url: str,
    cluster: str,
    token_file: Optional[str] = None,
    token: Optional[str] = None,
    verify: bool = True,
    out_base: Path | str = "./ceph-artifacts",
    mount_root_default: str = "/mnt/cephfs",
) -> Dict[str, Any]:
    """
    Build artifacts for a specific CephX user (entity like ``client.foo``).

    :param user_entity: CephX entity such as ``client.alice``.
    :type user_entity: str
    :param base_url: Ceph Manager API base URL.
    :type base_url: str
    :param cluster: Target cluster name.
    :type cluster: str
    :param token_file: Path to token file.
    :type token_file: str | None, optional
    :param token: Raw token string.
    :type token: str | None, optional
    :param verify: Whether to verify TLS certificates.
    :type verify: bool, optional
    :param out_base: Output directory root.
    :type out_base: pathlib.Path | str, optional
    :param mount_root_default: Mount root used by the script.
    :type mount_root_default: str, optional
    :return: Summary dictionary from :meth:`CephFsUtils.build_for_user_from_api`.
    :rtype: Dict[str, Any]
    """
    return CephFsUtils.build_for_user_from_api(
        user_entity=user_entity,
        base_url=base_url,
        cluster=cluster,
        token_file=token_file,
        token=token,
        verify=verify,
        out_base=out_base,
        mount_root_default=mount_root_default,
    )


def build_ceph_bundle_for_login(
    *,
    login: str,
    base_url: str,
    cluster: str,
    token_file: Optional[str] = None,
    token: Optional[str] = None,
    verify: bool = True,
    out_base: Path | str = "./ceph-artifacts",
    mount_root_default: str = "/mnt/cephfs",
) -> Dict[str, Any]:
    """
    Build artifacts for a bastion login (entity assumed as ``client.<login>``).

    :param login: Bastion login name.
    :type login: str
    :param base_url: Ceph Manager API base URL.
    :type base_url: str
    :param cluster: Target cluster name.
    :type cluster: str
    :param token_file: Path to token file.
    :type token_file: str | None, optional
    :param token: Raw token string.
    :type token: str | None, optional
    :param verify: Whether to verify TLS certificates.
    :type verify: bool, optional
    :param out_base: Output directory root.
    :type out_base: pathlib.Path | str, optional
    :param mount_root_default: Mount root used by the script.
    :type mount_root_default: str, optional
    :return: Summary dictionary from :meth:`CephFsUtils.build_for_login_from_api`.
    :rtype: Dict[str, Any]
    """
    return CephFsUtils.build_for_login_from_api(
        login=login,
        base_url=base_url,
        cluster=cluster,
        token_file=token_file,
        token=token,
        verify=verify,
        out_base=out_base,
        mount_root_default=mount_root_default,
    )
