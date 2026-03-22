# FABlib Technical Specification

## 1. Purpose

FABlib (fabrictestbed-extensions) provides a high-level Python API and CLI for
creating, managing, and interacting with experiments on the FABRIC testbed. It
abstracts the Fabric Information Model (FIM), orchestrator APIs, credential
management, and SSH operations behind a fluent, object-oriented interface.

## 2. System Boundaries

```
┌──────────────────────────────────────────────────────────┐
│                    User Code / Jupyter                     │
├──────────────────────────────────────────────────────────┤
│                    FABlib (this project)                   │
│  ┌─────────┐ ┌───────┐ ┌──────┐ ┌─────────┐ ┌────────┐ │
│  │FablibMgr│ │ Slice │ │ Node │ │Component│ │Network │ │
│  │ (Config)│ │       │ │      │ │         │ │Service │ │
│  └────┬────┘ └───┬───┘ └──┬───┘ └────┬────┘ └───┬────┘ │
├───────┼──────────┼────────┼──────────┼──────────┼───────┤
│       │    fabrictestbed (core library)          │       │
│  ┌────┴────┐ ┌───┴──────┐ ┌───────┴───────┐           │
│  │CredMgr │ │Orchestr. │ │  FIM Objects  │            │
│  │ Client  │ │ Client   │ │(ExperimentTopo│            │
│  └────┬────┘ └───┬──────┘ │ Node,Comp,..)│            │
│       │          │        └───────────────┘            │
├───────┼──────────┼─────────────────────────────────────┤
│       │   FABRIC Services (Remote)                      │
│  ┌────┴────┐ ┌───┴──────┐ ┌─────────┐ ┌────────────┐  │
│  │CredMgr │ │Orchestr. │ │ Bastion │ │ Ceph Mgr   │  │
│  │  API   │ │   API    │ │  Host   │ │   API      │  │
│  └────────┘ └──────────┘ └─────────┘ └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## 3. Module Specifications

### 3.1 FablibManager (`fablib.py`)

**Responsibility**: Top-level orchestrator. Authenticates users, discovers resources,
creates slices, manages SSH keys and bastion configuration.

**Inputs**:
- Configuration: fabric_rc file, environment variables, constructor kwargs
- Authentication: OAuth2 tokens via CredentialManager

**Outputs**:
- `Slice` objects (new or retrieved)
- Resource listings (sites, hosts, links, facility ports)
- SSH tunnel management

**State**:
- `slice_cache: Dict[str, Slice]` — in-memory slice cache (by name and ID)
- `ssh_thread_pool_executor: ThreadPoolExecutor` — for parallel SSH
- `runtime_config: dict` — resolved configuration values

**Key Invariants**:
- Configuration is immutable after construction
- Slice cache is maintained across operations (add/remove/update)
- Thread pool is shared across all slices

### 3.2 Slice (`slice.py`)

**Responsibility**: Experiment container. Holds topology (nodes, networks, ports),
manages lifecycle (submit/modify/renew/delete), tracks state.

**Inputs**:
- Topology operations: `add_node()`, `add_l2network()`, `add_l3network()`, etc.
- Lifecycle commands: `submit()`, `modify()`, `delete()`, `renew()`

**Outputs**:
- Child objects: `Node`, `NetworkService`, `FacilityPort`, `Switch`
- State info: `get_state()`, `isStable()`, error messages

**State**:
- `topology: ExperimentTopology` — FIM topology graph
- `nodes: Dict[str, Node]`
- `network_services: Dict[str, NetworkService]`
- `interfaces: Dict[str, Interface]`
- `_storage: bool` — default storage flag

**Key Invariants**:
- Topology is the single source of truth
- All child objects are created through slice methods (not directly)
- State transitions: `Nascent → Submitted → StableOK/StableError → Closed`

### 3.3 Node (`node.py`)

**Responsibility**: Compute resource (VM). Provides SSH access, file transfer,
command execution, post-boot configuration, network configuration.

**Inputs**:
- Capacity: cores, ram, disk, image, site, host
- Components: `add_component()`, `add_storage()`
- Commands: `execute()`, `upload_file()`, `download_file()`

**Outputs**:
- Command results: `(stdout, stderr)` tuples
- Network info: IP addresses, routes, interfaces
- State: reservation ID, state, error messages

**Key Invariants**:
- SSH always tunnels through bastion host
- Post-boot config runs sequentially: uploads → executes → network config
- Default: 2 cores, 8 GB RAM, 10 GB disk, Rocky 9 image

### 3.4 Component (`component.py`)

**Responsibility**: Hardware accelerator attached to a node. Maps user-friendly
model names to FIM component types.

**Model Map**:
```
NIC_Basic         → SharedNIC_ConnectX_6
NIC_ConnectX_6    → SmartNIC_ConnectX_6
GPU_TeslaT4       → GPU_Tesla_T4
NVME_P4510        → NVME_P4510
FPGA_Xilinx_U280  → FPGA_Xilinx_U280
... (14 models total)
```

### 3.5 Interface (`interface.py`)

**Responsibility**: Network port on a component or facility port. Manages IP
addresses, VLANs, bandwidth, and OS-level interface configuration.

**Configuration Modes**:
- `AUTO`: IP assigned automatically by network service
- `MANUAL`: User assigns IP explicitly

### 3.6 NetworkService (`network_service.py`)

**Responsibility**: Network connectivity service. Creates L2 bridges, point-to-point
links, L3 routed networks, and port mirrors.

**Service Types**: L2Bridge, L2PTP, L2STS, FABNetv4, FABNetv6, FABNetv4Ext,
FABNetv6Ext, L3VPN, PortMirror

### 3.7 Config (`config/config.py`)

**Responsibility**: Configuration resolution with strict precedence.

**Resolution Order**:
1. Constructor keyword arguments (highest priority)
2. Environment variables (`FABRIC_*`)
3. fabric_rc configuration file
4. Built-in defaults in `Constants` class

### 3.8 CLI (`cli/cli.py`)

**Responsibility**: Terminal interface via Click framework.

**Command Groups**:
- `configure setup` — First-time interactive setup
- `tokens create|refresh|revoke` — Token management
- `slices list|show|delete|renew|nodes|networks|interfaces|slivers`
- `resources sites|hosts|links|facility-ports`
- `user info|projects`

### 3.9 Utils (`utils/`)

**Modules**:
- `utils.py` — Table display, network reachability, file I/O, Jupyter detection
- `ceph_fs_utils.py` — CephFS credential building, mount script generation
- `slice.py` — Slice convenience methods (delete_all, find)
- `node.py` — SSH execution through bastion, IP validation
- `abc_utils.py` — Abstract base for test infrastructure

## 4. Data Flow

### Slice Creation Flow
```
User → FablibManager.new_slice(name)
     → Slice(topology=ExperimentTopology())
     → slice.add_node(name, site, cores, ram, disk)
        → Node(fim_node=topology.add_node())
     → slice.add_l2network(name, interfaces)
        → NetworkService(fim_ns=topology.add_network_service())
     → slice.submit()
        → orchestrator_proxy.create(topology)
     → slice.wait()
        → poll orchestrator until stable
     → node.execute("command")
        → paramiko SSH via bastion tunnel
```

### Configuration Flow
```
FablibManager(token_location=..., fabric_rc=...)
  → Config.__init__()
     → parse fabric_rc file → base config dict
     → overlay environment variables
     → overlay constructor kwargs
     → validate required fields
     → resolve file paths (expand ~, check existence)
  → build_slice_manager() → authenticate with CredMgr
  → verify_and_configure() → test connectivity
```

## 5. Error Handling

| Exception | Source | Meaning |
|---|---|---|
| `ConfigException` | Config | Missing/invalid configuration |
| `ConnectionError` | FablibManager | Cannot reach FABRIC services |
| `FabricManagerException` | fabrictestbed | Orchestrator API error |
| `TokenManagerException` | fabrictestbed | Token refresh failure |
| `SSHException` | paramiko | SSH connection failure |
| `TimeoutError` | Slice.wait() | Slice did not stabilize in time |

## 6. Thread Safety

- `FablibManager` maintains a shared `ThreadPoolExecutor` for SSH operations
- All `*_thread()` methods return `concurrent.futures.Future` objects
- Slice cache operations are not thread-safe (single-user assumed)
- FIM topology operations are not thread-safe

## 7. Supported OS Images

Rocky 8/9/10, CentOS 8/9/10, Ubuntu 20/22/24, Debian 11/12, Fedora 39/40,
FreeBSD 13/14, Kali, OpenBSD 7, Docker Rocky 9, Docker Ubuntu 22/24, BMv2
