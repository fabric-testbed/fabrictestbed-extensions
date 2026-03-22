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
- Legacy code still present (`fablib_old.py`, `slice_old.py`)
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
- [ ] Remove `fablib_old.py` and `slice_old.py` (deprecated legacy code)
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

## Technical Debt Tracker

| Item | Priority | Effort | Impact |
|---|---|---|---|
| Remove legacy `*_old.py` files | High | Low | Reduces confusion, -6,200 LOC |
| Add unit tests | High | Medium | Catches regressions, enables refactoring |
| Type annotations | Medium | Medium | Better IDE support, catches bugs |
| Extract SSH module | Medium | Medium | `node.py` is 4,800 LOC, hard to maintain |
| Consolidate resources v1/v2 | Medium | Low | Simpler API surface |
| Async SSH support | Low | High | Better performance for large slices |
| Plugin system | Low | High | Extensibility for new hardware |
