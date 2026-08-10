# Lint & Format Check

Check code formatting and style compliance for the FABlib project.

## Steps

1. Run black in check mode:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   python -m black --check --diff fabrictestbed_extensions/ tests/ 2>&1
   ```

2. Run isort in check mode:
   ```bash
   python -m isort --check --diff --profile black fabrictestbed_extensions/ tests/ 2>&1
   ```

3. Check docstring coverage with interrogate:
   ```bash
   python -m interrogate -v fabrictestbed_extensions/ --ignore-init-method --ignore-init-module --ignore-magic --ignore-module --ignore-nested-functions --ignore-nested-classes --ignore-private --ignore-semiprivate --fail-under 92.6 --exclude tests --exclude fabrictestbed_extensions/editors 2>&1
   ```

4. Report results:
   - Formatting issues found (files and line counts)
   - Import ordering issues
   - Docstring coverage percentage
   - Whether CI would pass or fail

If the user asks to fix issues, run `black` and `isort` without `--check`.
