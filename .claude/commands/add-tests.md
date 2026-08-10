# Add Tests

Generate unit tests for a specified module or class.

## Arguments

$ARGUMENTS - The module, class, or file to generate tests for.

## Instructions

1. Read the target source code thoroughly.

2. Identify testable behaviors:
   - Public method return values and side effects
   - Error handling (what exceptions are raised and when)
   - Edge cases (empty inputs, None values, boundary conditions)
   - Configuration precedence (if Config-related)
   - Validation logic

3. Write unit tests following these rules:
   - **No network access** — mock any HTTP/SSH calls
   - **No FABRIC credentials** — use dummy tokens and config
   - **Fast** — each test < 1 second
   - **Isolated** — clear env vars in setUp, use temp files
   - **Descriptive names** — `test_<method>_<scenario>_<expected>`

4. Place test files in `tests/unit/`:
   - `test_config.py` for Config tests
   - `test_validator.py` for NodeValidator tests
   - `test_utils.py` for Utils tests
   - `test_ceph_fs.py` for CephFsUtils tests
   - `test_template.py` for TemplateMixin tests
   - `test_cli.py` for CLI command tests

5. Use standard patterns:
   ```python
   import unittest
   from unittest.mock import MagicMock, patch

   class TestClassName(unittest.TestCase):
       def setUp(self):
           # Clear environment, create temp files
           pass

       def test_method_normal_case(self):
           # Arrange → Act → Assert
           pass

       def test_method_error_case(self):
           with self.assertRaises(ExpectedException):
               # trigger error
               pass
   ```

6. Run the tests to verify they pass:
   ```bash
   python -m pytest tests/unit/ -v --tb=short
   ```
