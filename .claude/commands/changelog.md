# Draft CHANGELOG Entry

Generate a CHANGELOG.md entry for recent changes on the current branch.

## Instructions

1. Analyze what changed:
   ```bash
   cd /mnt/scratch_nvme/work/fabrictestbed-extensions
   git log main..HEAD --oneline 2>&1
   git diff main --stat 2>&1
   git diff main -- fabrictestbed_extensions/ 2>&1
   ```

2. Categorize changes using Keep a Changelog format:
   - **Added**: New features, methods, CLI commands
   - **Changed**: Modifications to existing behavior
   - **Deprecated**: Features that will be removed
   - **Removed**: Features that were removed
   - **Fixed**: Bug fixes
   - **Security**: Security-related changes

3. For each change:
   - Write a one-line description in imperative mood
   - Reference GitHub issue/PR numbers if found in commit messages
   - Mention the method/class name for API changes
   - Note any breaking changes prominently

4. Read the existing CHANGELOG.md to match its style:
   ```bash
   head -30 CHANGELOG.md
   ```

5. Draft the entry at the top of the changelog, under a new version header
   or under "## Unreleased" if the version isn't decided.

## Output Format

```markdown
## [Unreleased]

### Added
- Add `method_name()` for [description] (Issue #N, PR #N)

### Changed
- Update [description] to [new behavior]

### Fixed
- Fix [bug description] that caused [symptom] (Issue #N)
```
