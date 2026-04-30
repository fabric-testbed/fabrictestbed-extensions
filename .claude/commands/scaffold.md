# Scaffold New Feature

Generate boilerplate code for a new FABlib feature, following all project conventions.

## Arguments

$ARGUMENTS - Description of what to scaffold. Examples:
- "new component model GPU_H100"
- "new network service type L3Multicast"
- "new CLI command 'slices export'"
- "new utility module ip_utils"
- "new mixin StorageMixin"

## Instructions

1. Parse the scaffold request to determine what type of feature is being added.

2. Read analogous existing code to understand the pattern:
   - New component model → read `constants.py` (model maps), `component.py`
   - New network service → read `network_service.py`, `constants.py`
   - New CLI command → read `cli/cli.py` (Click groups and commands)
   - New utility module → read `utils/utils.py` pattern
   - New mixin → read `template_mixin.py`

3. Generate boilerplate that includes:
   - Proper imports following isort conventions
   - Class/function stubs with complete Google-style docstrings
   - Type annotations on all signatures
   - `logging.getLogger("fablib")` (never root logger)
   - `_invalidate_cache()` calls if state changes
   - FIM wrapping if applicable

4. Generate corresponding test file in `tests/unit/` with:
   - setUp/tearDown methods
   - Test stubs for each public method
   - Mock patterns for dependencies

5. Generate CHANGELOG.md entry draft.

6. List all files that need modification (not just new files).

## Output

- Generated source files with full boilerplate
- Generated test file
- CHANGELOG entry
- List of existing files that need updates (e.g., `__init__.py`, `constants.py`)
