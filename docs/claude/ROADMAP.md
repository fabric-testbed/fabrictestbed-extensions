# FABlib Development Roadmap

## Current State (v2.0.2)

### Strengths
- Comprehensive slice lifecycle API (create, submit, modify, renew, delete)
- 14 hardware component models supported
- 9 network service types (L2/L3/VPN/Mirror)
- CephFS distributed storage integration
- Full CLI with interactive setup
- Sphinx API docs with 92.6%+ docstring coverage
- CI/CD with multi-platform testing

### Areas for Improvement
- Unit test coverage is minimal (1 test file, ~12 tests)
- ~~Legacy code still present (`fablib_old.py`, `slice_old.py`)~~ (removed)
- No type stubs or `py.typed` marker
- No async/await support (all SSH is synchronous + thread pool)
- Editor modules tightly coupled to Jupyter

---

## Short-Term (Next 1-2 Releases)

### Testing Expansion
- [ ] Add unit tests for `Config` class (precedence, validation, edge cases)
- [ ] Add unit tests for `NodeValidator` (allocation logic)
- [ ] Add unit tests for `CephFsUtils` (keyring parsing, mount script generation)
- [ ] Add unit tests for `TemplateMixin` (rendering, caching, dirty flags)
- [ ] Add unit tests for `Utils` (table display, IP helpers, reachability)
- [ ] Add unit tests for CLI commands (Click testing)
- [ ] Mock-based tests for `Slice` and `Node` without network access
- [ ] Target: 60%+ unit test coverage

### Code Quality
- [x] Remove `fablib_old.py` and `slice_old.py` (deprecated legacy code)
- [ ] Add `py.typed` marker for PEP 561 compliance
- [ ] Add type annotations to remaining untyped methods
- [ ] Consolidate `resources.py` and `resources_v2.py` (v1 appears unused)
- [ ] Extract SSH operations into dedicated `ssh.py` module from `node.py`

### Documentation
- [ ] Add usage examples in Sphinx docs (not just API reference)
- [ ] Document common error scenarios and troubleshooting
- [ ] Add architecture diagrams to RTD

---

## Medium-Term (v2.1 - v2.2)

### API Improvements
- [ ] Async slice operations (`async submit()`, `async wait()`)
- [ ] Context manager for slices (`with fablib.slice("name") as s:`)
- [ ] Structured logging with correlation IDs per slice/node
- [ ] Retry decorators for transient SSH/API failures
- [ ] Progress callbacks (not just boolean `progress` flag)

### CLI Enhancements
- [ ] `fabric-cli ssh <node>` — direct SSH to a node
- [ ] `fabric-cli watch <slice>` — live status updates
- [ ] `fabric-cli template apply <file>` — create slice from YAML/JSON template
- [ ] Tab completion for site names, slice names, component models
- [ ] JSON/CSV output for all commands (machine-readable)

### Storage
- [ ] Multi-cluster CephFS mounts per node
- [ ] Storage quota management
- [ ] Persistent volume lifecycle tied to slice lifecycle

### Observability
- [ ] Structured JSON logging option
- [ ] OpenTelemetry traces for slice operations
- [ ] Metrics collection (operation latency, success rate)

---

## Long-Term (v3.0)

### Architecture
- [ ] Full async/await rewrite (aioparamiko or asyncssh)
- [ ] Plugin system for custom component types
- [ ] Declarative slice definitions (YAML/TOML → slice)
- [ ] Diff-based slice modification (detect changes, apply delta)
- [ ] Event-driven model (webhooks/callbacks for state changes)

### Testing
- [ ] Property-based testing for topology validation
- [ ] Chaos testing framework for resilience
- [ ] Performance regression benchmarks in CI
- [ ] Integration test environment with mock FABRIC services

### Ecosystem
- [ ] Terraform provider for FABRIC resources
- [ ] GitHub Actions for FABRIC experiments
- [ ] VS Code extension for slice visualization
- [ ] REST API wrapper for non-Python users

---

## Performance Optimizations

### Quick Wins (1-2 sprints)
- [ ] Fix redundant FIM property lookups in `node.py` — `get_cores()` etc. call `get_fim().get_property()` twice instead of storing result (~30% speedup for node queries)
- [ ] Implement SSH connection pooling in `node.py` — every `execute()` creates a new bastion+node connection; cache and reuse (~40% latency reduction for parallel commands)
- [ ] Lightweight slice polling in `slice.py` — `wait()` fetches full slice state every 10s; use lightweight state-only query (~80% reduction in polling overhead)
- [ ] Avoid unnecessary `dict()` copy in `toDict()` — return cached dict directly when no skip filter is applied

### Medium-Term (2-3 sprints)
- [ ] Bulk sliver fetch — Node constructor individually fetches its sliver (N+1 pattern); bulk-fetch at Slice level and cache by reservation_id
- [ ] Lazy FablibManager initialization — defer `__build_manager()` and `verify_and_configure()` to first use instead of `__init__`
- [ ] Automatic cache invalidation — `_invalidate_cache()` should trigger automatically after `slice.update()`, not require manual calls

### Advanced (large slice scale, 100+ nodes)
- [ ] Parallel component/interface discovery — `Node.update()` fetches FIM data sequentially; parallelize across nodes using ThreadPoolExecutor
- [ ] Configurable thread pool sizing — expose `ssh_thread_pool_executor` size for runtime adjustment, allow auto-scaling
- [ ] Batch SSH operations helper — CephFS setup and post-boot config should reuse connections across multiple commands per node

---

## Usability Improvements

### API Consistency (High Priority)
- [ ] Standardize `show_*()` vs `list_*()` — currently `show_site()` returns `str` while `show_config()` returns a table object; unify return types
- [ ] Clarify `get_*()` vs `list_*()` — `get_nodes()` returns `List[Node]` but `list_nodes()` returns a table; rename or document clearly to avoid confusion
- [ ] Replace `print()` with `logging` — `submit()`, `wait()`, `post_boot_config()` print progress directly to stdout; use `logging.getLogger("fablib")` instead so scripting/automation isn't polluted
- [ ] Add global output format config — `fablib.set_default_output("json")` to avoid passing `output=` to every method

### Error Handling & Feedback (High Priority)
- [ ] Add specific exception types — replace generic `Exception` with `SliceTimeoutError`, `SliceAllocationError`, `SliceStateError` for better error handling
- [ ] Improve error messages — timeout errors should include last known sliver states and troubleshooting hints, not just "Timeout exceeded"
- [ ] Eliminate bare `except:` clauses — `node.py` silently swallows exceptions (e.g., `set_username()` failure); catch specific exceptions and log warnings
- [ ] Enforce state transitions — raise exceptions when methods are called in wrong state (e.g., `execute()` before `wait()`) instead of failing with cryptic errors

### Workflow Simplification (Medium Priority)
- [ ] Track post-boot-config state — add `slice.is_configured()` method; raise error if `post_boot_config()` called twice; make it automatic even for non-blocking submit
- [ ] Simplify `submit()` signature — 12 parameters is too many; group lease options separately or use a config object
- [ ] Add convenience methods — `slice.execute_on_all_nodes(cmd)`, `slice.get_all_interfaces()`, `slice.get_interfaces_for_network(net)`
- [ ] Add node filter methods — `slice.get_nodes(site="RENC")`, `slice.get_nodes(image="rocky_9")` instead of manual list filtering

### Discoverability & Onboarding (Medium Priority)
- [ ] Add resource browser — `fablib.resources.sites()`, `.images()`, `.components()`, `.find_sites(has_gpu=True)` for unified discovery
- [ ] Better config setup errors — "Missing Token File" should say where to put it and which env var to set, not just raise `ConfigException`
- [ ] Add `FablibManager.interactive_setup()` — walk through configuration from Python REPL (complement to `fabric-cli configure`)
- [ ] Document state machine — clearly show `Nascent → Submitted → StableOK/StableError → Closed` transitions in docstrings

### Output Consistency (Low Priority)
- [ ] Standardize JSON output — always return parsed `dict` for `output="json"`, let user serialize if needed
- [ ] Document output schemas per method
- [ ] Ensure table outputs fit standard 120-char terminals

---

## Technical Debt Tracker

| Item | Priority | Effort | Impact |
|---|---|---|---|
| ~~Remove legacy `*_old.py` files~~ | ~~High~~ | ~~Low~~ | Done — removed 6,159 LOC |
| Add unit tests | High | Medium | Catches regressions, enables refactoring |
| Type annotations | Medium | Medium | Better IDE support, catches bugs |
| Extract SSH module | Medium | Medium | `node.py` is 4,800 LOC, hard to maintain |
| Consolidate resources v1/v2 | Medium | Low | Simpler API surface |
| Async SSH support | Low | High | Better performance for large slices |
| Plugin system | Low | High | Extensibility for new hardware |
