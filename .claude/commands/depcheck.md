# Dependency and Compatibility Check

Check for dependency issues, version conflicts, and compatibility problems.

## Instructions

1. Read the current dependency specification:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   cat pyproject.toml
   ```

2. Check for version pinning issues:
   - Over-pinned dependencies (`==` where `>=` would be better)
   - Under-pinned dependencies (missing version constraints)
   - Duplicate dependencies

3. Check import compatibility:
   ```bash
   python -c "import fabrictestbed_extensions; print(fabrictestbed_extensions.__version__)" 2>&1
   ```

4. Check for deprecated dependency usage:
   - Search for deprecated API patterns in imports
   - Verify compatibility with Python 3.11, 3.12, 3.13

5. Analyze the dependency tree:
   ```bash
   pip show fabrictestbed-extensions 2>&1
   pip show fabrictestbed 2>&1
   ```

6. Check for missing optional dependencies:
   - Are all imports guarded with try/except for optional deps?
   - Do test dependencies match what tests actually import?

## Output

```
Dependency Report
=================

Issues Found:
  [WARN] ...
  [INFO] ...

Version Compatibility:
  Python 3.11: OK
  Python 3.12: OK
  Python 3.13: [check needed]

Dependency Tree:
  fabrictestbed-extensions 2.0.2
  ├── fabrictestbed 2.0.3
  ├── paramiko X.X
  ...

Recommendations:
1. ...
2. ...
```
