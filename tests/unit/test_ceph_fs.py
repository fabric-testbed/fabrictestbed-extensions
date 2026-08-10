"""Unit tests for CephFsUtils."""

import os
import tempfile
import unittest

from fabrictestbed_extensions.utils.ceph_fs_utils import CephFsUtils


class TestCephFsUtilsInit(unittest.TestCase):
    """Tests for CephFsUtils constructor and validation."""

    SAMPLE_KEYRING = (
        "[client.testuser]\n"
        "\tkey = AQBkeybase64==\n"
        '\tcaps mds = "allow rw fsname=cephfs path=/testpath"\n'
        '\tcaps mon = "allow r"\n'
        '\tcaps osd = "allow rw"\n'
    )

    SAMPLE_CONF = "[global]\nmon_host = 10.0.0.1\n"

    def test_empty_cluster_raises(self):
        with self.assertRaises(ValueError) as ctx:
            CephFsUtils(
                cluster="",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=self.SAMPLE_KEYRING,
            )
        self.assertIn("non-empty", str(ctx.exception))

    def test_whitespace_cluster_raises(self):
        with self.assertRaises(ValueError):
            CephFsUtils(
                cluster="   ",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=self.SAMPLE_KEYRING,
            )

    def test_valid_initialization(self):
        utils = CephFsUtils(
            cluster="test-cluster",
            ceph_conf_text=self.SAMPLE_CONF,
            keyring_blob=self.SAMPLE_KEYRING,
        )
        self.assertEqual(utils.cluster, "test-cluster")
        self.assertEqual(utils.mount_root_default, "/mnt/cephfs")
        self.assertIsNone(utils.entity)
        self.assertIsNone(utils.user_only)

    def test_custom_mount_root(self):
        utils = CephFsUtils(
            cluster="test",
            ceph_conf_text=self.SAMPLE_CONF,
            keyring_blob=self.SAMPLE_KEYRING,
            mount_root_default="/custom/mount",
        )
        self.assertEqual(utils.mount_root_default, "/custom/mount")


class TestCephFsUtilsBuild(unittest.TestCase):
    """Tests for CephFsUtils.build() output."""

    SAMPLE_KEYRING = (
        "[client.alice]\n"
        "\tkey = AQBTestKeyBase64==\n"
        '\tcaps mds = "allow rw fsname=myfs path=/data"\n'
        '\tcaps mon = "allow r"\n'
        '\tcaps osd = "allow rw"\n'
    )

    SAMPLE_CONF = "[global]\nmon_host = 10.0.0.1:6789\n"

    def test_build_creates_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            utils = CephFsUtils(
                cluster="testcluster",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=self.SAMPLE_KEYRING,
                out_base=tmpdir,
            )
            result = utils.build()

            # Check returned keys
            self.assertIn("cluster_dir", result)
            self.assertIn("ceph_conf", result)
            self.assertIn("secret_file", result)
            self.assertIn("keyring_file", result)
            self.assertIn("mount_script", result)
            self.assertIn("entity", result)
            self.assertIn("user", result)
            self.assertIn("mounts", result)

            # Check entity parsing
            self.assertEqual(result["entity"], "client.alice")
            self.assertEqual(result["user"], "alice")

            # Check files exist
            self.assertTrue(os.path.isfile(result["ceph_conf"]))
            self.assertTrue(os.path.isfile(result["secret_file"]))
            self.assertTrue(os.path.isfile(result["keyring_file"]))
            self.assertTrue(os.path.isfile(result["mount_script"]))

            # Check mount points
            self.assertEqual(len(result["mounts"]), 1)
            mount = result["mounts"][0]
            self.assertEqual(mount["fsname"], "myfs")
            self.assertEqual(mount["path"], "/data")
            self.assertIn("testcluster", mount["mount_point"])
            self.assertIn("alice", mount["mount_point"])

    def test_build_with_json_escaped_keyring(self):
        import json

        json_keyring = json.dumps(self.SAMPLE_KEYRING)

        with tempfile.TemporaryDirectory() as tmpdir:
            utils = CephFsUtils(
                cluster="testcluster",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=json_keyring,
                out_base=tmpdir,
            )
            result = utils.build()
            self.assertEqual(result["entity"], "client.alice")

    def test_build_conf_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            utils = CephFsUtils(
                cluster="testcluster",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=self.SAMPLE_KEYRING,
                out_base=tmpdir,
            )
            result = utils.build()

            with open(result["ceph_conf"]) as f:
                conf_content = f.read()
            self.assertIn("mon_host", conf_content)

    def test_build_mount_script_is_executable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            utils = CephFsUtils(
                cluster="testcluster",
                ceph_conf_text=self.SAMPLE_CONF,
                keyring_blob=self.SAMPLE_KEYRING,
                out_base=tmpdir,
            )
            result = utils.build()

            script_path = result["mount_script"]
            self.assertTrue(os.access(script_path, os.X_OK))

    def test_build_multiple_fs_paths(self):
        keyring = (
            "[client.bob]\n"
            "\tkey = AQBKeyForBob==\n"
            '\tcaps mds = "allow rw fsname=fs1 path=/alpha, allow rw fsname=fs2 path=/beta"\n'
            '\tcaps mon = "allow r"\n'
            '\tcaps osd = "allow rw"\n'
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            utils = CephFsUtils(
                cluster="multi",
                ceph_conf_text="[global]\n",
                keyring_blob=keyring,
                out_base=tmpdir,
            )
            result = utils.build()
            self.assertEqual(len(result["mounts"]), 2)
            fsnames = {m["fsname"] for m in result["mounts"]}
            self.assertIn("fs1", fsnames)
            self.assertIn("fs2", fsnames)
