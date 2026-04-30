# Test Coverage Analysis

Analyze test coverage and identify the highest-value areas to add tests.

## Arguments

$ARGUMENTS - Optional: specific module to analyze. If empty, analyze the full project.

## Instructions

1. Run tests with coverage:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   python -m pytest tests/unit/ --cov=fabrictestbed_extensions --cov-report=term-missing -v 2>&1
   ```

2. If a specific module was requested, also run:
   ```bash
   python -m pytest tests/unit/ --cov=fabrictestbed_extensions/<module> --cov-report=term-missing -v 2>&1
   ```

3. Analyze the coverage report:
   - Identify modules with 0% coverage
   - Identify modules with coverage below 50%
   - Find specific uncovered lines/branches

4. Prioritize by impact:

   | Module | Target | Priority |
   |---|---|---|
   | `config/config.py` | 80% | High — config bugs break everything |
   | `validator.py` | 90% | High — pure functions, easy to test |
   | `utils/utils.py` | 70% | High — widely used helpers |
   | `utils/ceph_fs_utils.py` | 70% | Medium — storage feature |
   | `template_mixin.py` | 80% | Medium — cross-cutting concern |
   | `cli/cli.py` | 50% | Medium — user-facing |
   | `constants.py` | 50% | Low — mostly constants |

5. For each uncovered area, suggest:
   - What test to write (test name and brief description)
   - What to mock (list dependencies)
   - Expected difficulty (easy/medium/hard)

## Output

```
Test Coverage Report
====================
Overall Coverage: XX.X%

Module Coverage:
  config/config.py        XX.X%  (target: 80%)
  validator.py            XX.X%  (target: 90%)
  ...

Top 10 Highest-Value Test Additions:
1. test_config_env_var_precedence — Config class, mock env vars (easy)
2. test_validator_node_fits_host — NodeValidator, no mocking needed (easy)
...

Estimated Coverage After Additions: XX.X%
```
