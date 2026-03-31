# Run Tests

Run the FABlib test suite and report results.

## Steps

1. Run unit tests with pytest:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   python -m pytest tests/unit/ -v --tb=short 2>&1
   ```

2. If any tests fail, read the failing test file and the source code it tests.

3. Diagnose the root cause of failures. Common issues:
   - Environment variables leaking between tests (setUp should clear them)
   - Missing test fixtures in tests/unit/data/
   - Import errors from missing dependencies

4. Report a summary:
   - Total tests run, passed, failed, skipped
   - For each failure: test name, error type, one-line description
   - Suggested fixes if obvious

Do NOT fix the tests automatically — just report findings.
