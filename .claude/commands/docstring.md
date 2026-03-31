# Add/Fix Docstrings

Add or improve docstrings to meet the project's 92.6% coverage requirement.

## Arguments

$ARGUMENTS - The module, class, or file to add docstrings to. If empty, scan the
entire project for missing docstrings.

## Instructions

1. If a specific target is given, read that file. Otherwise, run interrogate to find
   files below threshold:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   python -m interrogate -v fabrictestbed_extensions/ --ignore-init-method --ignore-init-module --ignore-magic --ignore-module --ignore-nested-functions --ignore-nested-classes --ignore-private --ignore-semiprivate --exclude tests --exclude fabrictestbed_extensions/editors 2>&1
   ```

2. For each public method missing a docstring:
   - Read the method body to understand what it does
   - Read callers to understand how it's used
   - Write a Google-style docstring with:
     - Brief description (first line)
     - Detailed description (if non-obvious)
     - `:param name:` and `:type name:` for each parameter
     - `:return:` and `:rtype:` for return value
     - `:raises ExceptionType:` for raised exceptions

3. Style rules:
   - First line is imperative mood ("Gets the name", not "This gets the name")
   - Keep first line under 80 chars
   - Use `:rtype: str` not `:rtype: String`

4. After adding docstrings, verify coverage:
   ```bash
   python -m interrogate -v <target_module> --ignore-init-method --ignore-init-module --ignore-magic --ignore-module --ignore-nested-functions --ignore-nested-classes --ignore-private --ignore-semiprivate 2>&1
   ```

5. Run black to ensure formatting is correct:
   ```bash
   python -m black <files> 2>&1
   ```

## Output

- Modified files with docstrings added
- Coverage report before and after
- Count of docstrings added
