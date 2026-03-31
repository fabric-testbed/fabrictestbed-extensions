# Code Review

Review staged or recent changes against FABlib project standards.

## Instructions

Review the current git diff (staged + unstaged changes) for:

### Must-Fix Issues
1. **Missing docstrings** on new public methods (interrogate requires 92.6%+)
2. **Root logger usage** — must use `logging.getLogger("fablib")`
3. **FIM objects exposed** in public API — must be wrapped
4. **Missing cache invalidation** — new cached properties need `_invalidate_cache()`
5. **Hardcoded URLs** — must use `Constants` class
6. **Security issues** — command injection, credential leaks, unsafe SSH
7. **Missing error handling** on network/SSH operations

### Style Issues
8. **Formatting** — would `black` and `isort` change this code?
9. **Naming** — PascalCase classes, snake_case methods, UPPER_SNAKE constants
10. **Unused imports** or dead code

### Best Practices
11. **CHANGELOG.md** updated for user-facing changes?
12. **Tests** added or updated for new functionality?
13. **Type annotations** on new method signatures?

## Steps

1. Run `git diff HEAD` to see all changes
2. Read each modified file to understand context
3. Produce a review with:
   - **Blockers**: Issues that must be fixed before merge
   - **Suggestions**: Improvements that would be nice
   - **Praise**: Things done well

Keep the review concise and actionable.
