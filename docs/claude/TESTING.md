# FABlib Testing Guide

## Test Infrastructure

### Directory Structure

```
tests/
├── unit/                    # Fast, no network access required
│   ├── __init__.py
│   ├── data/
│   │   └── dummy_fabric_rc  # Test fixture: minimal config file
│   ├── test_basic.py        # FablibManager configuration tests
│   ├── test_config.py       # Config class tests (NEW)
│   ├── test_validator.py    # NodeValidator tests (NEW)
│   ├── test_utils.py        # Utils helper tests (NEW)
│   ├── test_ceph_fs.py      # CephFsUtils tests (NEW)
│   └── test_template.py     # TemplateMixin tests (NEW)
├── integration/             # Requires FABRIC credentials & network
│   ├── abc_test.py          # Base class for integration tests
│   ├── test_hello_fabric.py # Basic slice lifecycle
│   ├── test_fablib_node.py  # Node operations
│   ├── test_bastion_ssh.py  # SSH connectivity
│   ├── test_list_resources.py
│   ├── test_modify.py
│   ├── test_L2_reconfig_post_reboot.py
│   ├── test_fabnetv4_ext.py
│   └── component_tests.py
└── benchmarks/              # Performance testing
    ├── gpu_tesla_t4_benchmark.py
    ├── link_benchmark.py
    ├── local_network_benchmark.py
    ├── network_benchmark_tests.py
    └── nvme_benchmark.py
```

### Running Tests

```bash
# Unit tests (default, CI-safe)
tox                          # Full tox run
pytest tests/unit/           # Direct pytest
pytest tests/unit/ -v        # Verbose output
pytest tests/unit/ -k "test_config"  # Run specific tests

# Integration tests (requires FABRIC setup)
tox -e integration
pytest -s tests/integration/test_hello_fabric.py

# Benchmarks
tox -e benchmarks

# With coverage
pytest tests/unit/ --cov=fabrictestbed_extensions --cov-report=html

# Format check (not tests, but part of CI)
tox -e format
```

### CI Configuration

Tests run on GitHub Actions across:
- **Python versions**: 3.11, 3.12, 3.13
- **Operating systems**: Ubuntu, Windows, macOS
- **Coverage**: Reported to Coveralls

## Writing Unit Tests

### Principles

1. **No network access** — unit tests must not call FABRIC APIs or SSH
2. **No FABRIC credentials** — don't assume tokens or keys exist
3. **Fast** — each test should complete in <1 second
4. **Isolated** — clear environment variables in setUp, use temp files
5. **Focused** — test one behavior per test method

### Pattern: Testing Configuration

```python
import os
import tempfile
import unittest

from fabrictestbed_extensions.fablib.config.config import Config, ConfigException
from fabrictestbed_extensions.fablib.constants import Constants


class ConfigTests(unittest.TestCase):
    def setUp(self):
        os.environ.clear()
        self.rcfile = tempfile.NamedTemporaryFile(mode="w", suffix="_fabric_rc")

    def tearDown(self):
        self.rcfile.close()

    def test_env_var_overrides_config_file(self):
        """Environment variables take precedence over fabric_rc."""
        self.rcfile.write("export FABRIC_PROJECT_ID=from_file\n")
        self.rcfile.flush()
        os.environ["FABRIC_PROJECT_ID"] = "from_env"
        # ... assert config resolves to "from_env"

    def test_missing_required_field_raises(self):
        """ConfigException when required field is missing."""
        with self.assertRaises(ConfigException):
            Config(fabric_rc=self.rcfile.name)
```

### Pattern: Testing Validators

```python
class NodeValidatorTests(unittest.TestCase):
    def test_node_fits_in_host(self):
        host = {
            "name": "host1", "state": "Active",
            "cores_available": 32, "ram_available": 128,
            "disk_available": 1000, "components": {}
        }
        # ... create mock node, test can_allocate_node_in_host()

    def test_inactive_host_rejected(self):
        host = {"name": "host1", "state": "Maintenance", ...}
        # ... assert allocation fails
```

### Pattern: Testing Utilities

```python
class UtilsTests(unittest.TestCase):
    def test_valid_ipv4(self):
        from fabrictestbed_extensions.utils.node import NodeUtils
        self.assertEqual(NodeUtils.validIPAddress("192.168.1.1"), "IPv4")

    def test_valid_ipv6(self):
        self.assertEqual(NodeUtils.validIPAddress("::1"), "IPv6")

    def test_invalid_ip(self):
        self.assertEqual(NodeUtils.validIPAddress("not_an_ip"), "Invalid")
```

### Pattern: Testing CephFS Utils

```python
class CephFsUtilsTests(unittest.TestCase):
    def test_parse_keyring(self):
        keyring = "[client.user]\n\tkey = AQAA...==\n"
        # ... verify parsing extracts key correctly

    def test_mount_script_generation(self):
        # ... verify generated script has correct mount point
```

## Writing Integration Tests

### Prerequisites

1. Valid FABRIC token at configured location
2. Active FABRIC project membership
3. Network access to FABRIC services
4. Bastion SSH key configured

### Pattern: Integration Test

```python
import unittest
from fabrictestbed_extensions.fablib.fablib import FablibManager


class MyIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fablib = FablibManager()
        cls.slice_name = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def test_slice_lifecycle(self):
        slice = self.fablib.new_slice(name=self.slice_name)
        node = slice.add_node(name="n1", site="RENC")
        slice.submit()
        slice.wait(timeout=600)
        self.assertTrue(slice.isStable())
        stdout, stderr = node.execute("hostname")
        self.assertIn("n1", stdout)

    @classmethod
    def tearDownClass(cls):
        try:
            slice = cls.fablib.get_slice(cls.slice_name)
            slice.delete()
        except Exception:
            pass
```

### Best Practices

- Always use unique slice names (include timestamp)
- Always clean up slices in `tearDownClass`
- Use `slice.wait(timeout=600)` — allocation can take minutes
- Check `slice.isStable()` before executing commands
- Use random sites (`fablib.get_random_site()`) for load distribution

## Test Coverage Goals

| Module | Current | Target |
|---|---|---|
| `config/config.py` | ~0% | 80% |
| `validator.py` | 0% | 90% |
| `constants.py` | 0% | 50% (constants are trivial) |
| `utils/utils.py` | 0% | 70% |
| `utils/ceph_fs_utils.py` | 0% | 70% |
| `template_mixin.py` | 0% | 80% |
| `cli/cli.py` | 0% | 50% |
| `fablib.py` | ~5% | 30% (hard to unit test) |
| `slice.py` | ~0% | 20% (needs mocking) |
| `node.py` | ~0% | 20% (needs mocking) |

## Mocking Strategy

For classes that depend on FABRIC services, use `unittest.mock`:

```python
from unittest.mock import MagicMock, patch

@patch('fabrictestbed_extensions.fablib.fablib.FablibManager.build_slice_manager')
def test_something(self, mock_build):
    mock_build.return_value = MagicMock()
    fablib = FablibManager(offline=True, ...)
    # ... test without network
```

Key things to mock:
- `FablibManager.build_slice_manager()` — avoids CredMgr calls
- `paramiko.SSHClient` — avoids SSH connections
- `requests.get/post` — avoids HTTP calls
- `fabric_ceph_client` — avoids Ceph API calls
