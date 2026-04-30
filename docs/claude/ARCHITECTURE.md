# FABlib Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
│   Jupyter Notebooks  │  Python Scripts  │  fabric-cli (Click)   │
└──────────┬───────────┴────────┬─────────┴──────────┬────────────┘
           │                    │                     │
┌──────────▼────────────────────▼─────────────────────▼────────────┐
│                    FABlib Public API                              │
│                                                                  │
│  FablibManager ─── creates ──→ Slice                             │
│       │                         ├── Node ──── Component          │
│       │                         │    └── Interface               │
│       │                         ├── NetworkService               │
│       │                         │    └── Interface               │
│       │                         ├── FacilityPort                 │
│       │                         │    └── Interface               │
│       │                         ├── Switch (extends Node)        │
│       │                         └── Attestable_Switch (ext Node) │
│       │                                                          │
│       ├── ResourcesV2 (site/host/link queries)                   │
│       ├── Site (per-site resource info)                           │
│       └── Artifact (reusable experiment assets)                  │
├──────────────────────────────────────────────────────────────────┤
│                    Internal Layer                                 │
│                                                                  │
│  Config ──── fabric_rc parsing, env vars, defaults               │
│  TemplateMixin ──── Jinja2 rendering, caching, toDict()          │
│  NodeValidator ──── resource allocation checks                   │
│  Utils ──── table display, SSH tunnels, network helpers          │
│  CephFsUtils ──── CephFS credential & mount management          │
├──────────────────────────────────────────────────────────────────┤
│                    External Dependencies                          │
│                                                                  │
│  fabrictestbed ──── FIM, Orchestrator client, CredMgr client     │
│  paramiko ──── SSH connections through bastion                   │
│  fabric_ceph_client ──── Ceph cluster management API             │
│  fabric_fss_utils ──── File system service utilities             │
│  pandas/numpy ──── Data processing for resource tables           │
│  ipycytoscape/ipyleaflet ──── Topology visualization             │
└──────────────────────────────────────────────────────────────────┘
```

## Package Structure

```
fabrictestbed_extensions/
├── __init__.py                  # Package version (__version__)
│
├── fablib/                      # Core library (26,600+ LOC)
│   ├── __init__.py
│   ├── fablib.py                # FablibManager — main entry point
│   ├── slice.py                 # Slice — experiment container
│   ├── node.py                  # Node — compute VM (largest file, 4,800 LOC)
│   ├── component.py             # Component — GPU/NIC/FPGA/NVMe
│   ├── interface.py             # Interface — network port
│   ├── network_service.py       # NetworkService — L2/L3 connectivity
│   ├── facility_port.py         # FacilityPort — external connections
│   ├── switch.py                # Switch — P4 programmable switch
│   ├── attestable_switch.py     # Attestable_Switch — attestable P4
│   ├── site.py                  # Site — testbed site info
│   ├── resources.py             # Resources — v1 resource queries
│   ├── resources_v2.py          # ResourcesV2 — v2 resource queries
│   ├── validator.py             # NodeValidator — allocation checks
│   ├── template_mixin.py        # TemplateMixin — Jinja2 + caching
│   ├── artifact.py              # Artifact — experiment assets
│   ├── constants.py             # Constants — all defaults & mappings
│   ├── config/
│   │   ├── config.py            # Config class — configuration management
│   │   ├── fabric_rc            # Shell config template
│   │   └── fabric_rc.yml        # YAML config template
│   └── ...
│
├── cli/                         # Command-line interface (2,400 LOC)
│   ├── __init__.py
│   ├── cli.py                   # Click commands & groups
│   └── exceptions.py            # CLI exceptions
│
├── editors/                     # Topology visualization (2,600 LOC)
│   ├── __init__.py
│   ├── abc_topology_editor.py   # Abstract base editor
│   ├── cytoscape_topology_editor.py  # Interactive graph
│   └── geo_topology_editor.py   # Geographic map view
│
├── utils/                       # Utilities (1,950 LOC)
│   ├── __init__.py
│   ├── utils.py                 # Display, network, I/O helpers
│   ├── ceph_fs_utils.py         # CephFS client management
│   ├── slice.py                 # Slice utility functions
│   ├── node.py                  # Node SSH helpers
│   └── abc_utils.py             # Abstract test utilities
│
├── ui/                          # UI components
│   ├── __init__.py
│   └── artifact_manager_ui.py   # Artifact browser
│
└── images/                      # Static assets
    ├── fabric_logo.png
    ├── server.png
    └── slice_rack.png
```

## Design Patterns

### 1. Builder Pattern (Slice Construction)

```python
# Users build experiment topology incrementally
slice = fablib.new_slice(name="experiment")
node1 = slice.add_node(name="node1", site="TACC", cores=8, ram=32)
gpu = node1.add_component(model="GPU_TeslaT4", name="gpu1")
nic = node1.add_component(model="NIC_ConnectX_6", name="nic1")
net = slice.add_l2network(name="lan", interfaces=[nic.get_interfaces()[0]])
slice.submit()
```

Each `add_*()` call modifies the underlying FIM `ExperimentTopology` and returns
a wrapper object. The topology is submitted atomically.

### 2. Factory Pattern (Object Creation)

Each resource class has a static `new_*()` factory method:

```python
Node.new_node(slice, name, site, ...)          # → Node
Component.new_component(node, model, name, ...) # → Component
Component.new_storage(node, name, ...)          # → Component
NetworkService.new_l2network(slice, ...)        # → NetworkService
NetworkService.new_l3network(slice, ...)        # → NetworkService
```

Factory methods encapsulate FIM object creation and validation.

### 3. TemplateMixin (Cross-Cutting Concerns)

Inherited by Node, Component, Interface, NetworkService, FacilityPort:

```python
class TemplateMixin:
    _fim_dirty: bool           # Tracks if FIM data changed
    _default_skip: List[str]   # Fields excluded from templates

    def toDict() -> dict                      # Serialize to dictionary
    def get_template_context() -> dict         # Jinja2 context from slice
    def render_template(input_string) -> str   # Render Jinja2 template
    def _invalidate_cache()                    # Clear cached properties
```

### 4. Configuration Strategy (Config Class)

```
Priority (high → low):
  1. Constructor kwargs     → FablibManager(token_location="...")
  2. Environment variables  → FABRIC_TOKEN_LOCATION=...
  3. fabric_rc file        → export FABRIC_TOKEN_LOCATION=...
  4. Built-in defaults      → Constants.DEFAULT_*

Config.REQUIRED_ATTRS = {
    "token_location":    {"env": "FABRIC_TOKEN_LOCATION", "default": "~/.fabric/..."},
    "orchestrator_host": {"env": "FABRIC_ORCHESTRATOR_HOST", "default": "..."},
    ...
}
```

### 5. FIM Wrapping

Every FABlib object wraps a corresponding FIM object:

| FABlib Class | FIM Object |
|---|---|
| `Slice.topology` | `ExperimentTopology` |
| `Node.fim_node` | `fim.user.Node` |
| `Component.fim_component` | `fim.slice_editor.Component` |
| `Interface.fim_interface` | `fim.user.interface.Interface` |
| `NetworkService.fim_ns` | `fim.slice_editor.NetworkService` |

FIM objects are never exposed in the public API. All access goes through
FABlib wrapper methods.

## Network Architecture

### SSH Tunneling

```
User Machine → Bastion Host → Experiment Node
               (SSH jump)      (management IP)
```

All SSH operations (execute, upload, download) tunnel through the bastion.
The bastion host, username, and key are configured via fabric_rc.

### Network Types

```
L2Bridge:  [Node A] ──ethernet── [Node B]     (same site)
L2PTP:     [Node A] ──ethernet── [Node B]     (cross-site, QoS)
L2STS:     [Node A] ──ethernet── [Node B]     (cross-site, best-effort)
FABNetv4:  [Node A] ──IPv4─┬── [Node B]       (routed, 10.128.0.0/10)
FABNetv6:  [Node A] ──IPv6─┴── [Node B]       (routed, 2602:FCFB::/40)
FABNetv4Ext: [Node] ──── [Internet]            (external IPv4)
FABNetv6Ext: [Node] ──── [Internet]            (external IPv6)
```

## CI/CD Pipeline

```
Push/PR → ┬─ test.yml ──────── pytest (Py 3.11-3.13, Linux/Mac/Win)
          ├─ build.yml ─────── flit build + install verification
          ├─ check_format.yml ─ black + isort + CHANGELOG check
          ├─ check_docstring_coverage.yml ─ interrogate (≥92.6%)
          └─ check_signed_commits.yml ──── GPG signature verification

Tag (rel*) → publish.yml ──── test → build → PyPI upload → GitHub release
```

## Storage Architecture (CephFS)

```
Node.enable_storage(cluster)
  → post_boot_config()
    → CephFsUtils.build()
      → fetch credentials from Ceph Manager API
      → write ceph.conf, keyring, secret files
      → generate mount script
    → execute mount script on node
    → persist storage metadata to orchestrator
```

Mount points: `/mnt/cephfs/<cluster>/<user>/<path_slug>/`

## File Size Distribution

| Module | LOC | % of Total |
|---|---|---|
| fablib/ (core) | 26,600 | 76% |
| cli/ | 2,400 | 7% |
| editors/ | 2,600 | 7% |
| utils/ | 1,950 | 6% |
| ui/ | 280 | 1% |
| tests/ | ~1,200 | 3% |
| **Total** | **~35,000** | **100%** |

The largest single files are `node.py` (4,800 LOC) and `slice.py` (3,600 LOC),
reflecting the breadth of operations available on compute nodes and experiment
containers.
