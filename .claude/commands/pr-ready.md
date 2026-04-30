# PR Readiness Check

Run all checks that GitHub CI will run, and report whether a PR is ready.

## Steps

Run these checks (report results for each):

1. **Unit Tests**
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   python -m pytest tests/unit/ -v --tb=short 2>&1
   ```

2. **Code Formatting (black)**
   ```bash
   python -m black --check fabrictestbed_extensions/ tests/ 2>&1
   ```

3. **Import Ordering (isort)**
   ```bash
   python -m isort --check --profile black fabrictestbed_extensions/ tests/ 2>&1
   ```

4. **Docstring Coverage (interrogate)**
   ```bash
   python -m interrogate fabrictestbed_extensions/ --ignore-init-method --ignore-init-module --ignore-magic --ignore-module --ignore-nested-functions --ignore-nested-classes --ignore-private --ignore-semiprivate --fail-under 92.6 --exclude tests --exclude fabrictestbed_extensions/editors 2>&1
   ```

5. **CHANGELOG Updated**
   ```bash
   git diff main -- CHANGELOG.md 2>&1
   ```

6. **Signed Commits**
   ```bash
   git log main..HEAD --format='%H %G?' 2>&1
   ```

## Report Format

```
PR Readiness Report
===================
Unit Tests:        PASS/FAIL (X passed, Y failed)
Black Formatting:  PASS/FAIL (N files need formatting)
Import Ordering:   PASS/FAIL
Docstring Coverage: PASS/FAIL (XX.X%)
CHANGELOG Updated: YES/NO
Signed Commits:    YES/NO/N/A

Overall: READY / NOT READY
```

List specific issues that need fixing before the PR can be submitted.
