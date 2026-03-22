# Generate Slice Template

Create a reusable FABlib slice template for a specific experiment topology.

## Arguments

$ARGUMENTS - Description of the desired experiment topology. Examples:
- "3-node cluster at TACC with GPUs and shared L2 network"
- "star topology with 1 router and 4 leaf nodes across 2 sites"
- "single node with ConnectX-6 NIC and external IPv4"
- "CephFS-enabled 2-node setup for data transfer testing"

## Instructions

1. Parse the topology request to identify:
   - Number and type of nodes
   - Site placement (specific sites or random)
   - Component requirements (NICs, GPUs, FPGAs, NVMe)
   - Network topology (L2/L3, single-site/cross-site)
   - Storage requirements (CephFS)
   - Image requirements

2. Read relevant source code to validate the configuration:
   - `constants.py` for valid component models and image names
   - `node.py` for default values (cores, ram, disk)
   - `network_service.py` for network type constraints
   - `slice.py` for the builder API

3. Generate a complete Python script that:
   - Creates the slice with a parameterized name
   - Adds all nodes with appropriate resources
   - Adds all components
   - Configures networks with proper interface assignments
   - Enables storage if requested
   - Submits, waits, and verifies stability
   - Runs post-boot configuration
   - Includes a cleanup/delete function

4. Validate constraints:
   - L2Bridge: same site only
   - L2PTP: exactly 2 interfaces, cross-site OK
   - L2STS: cross-site, best-effort
   - FABNetv4/v6: auto-IP assignment
   - SharedNIC (NIC_Basic): max 2 per node
   - Dedicated NIC: max 1 per physical NIC on host

5. Add a topology summary comment at the top of the script.

## Output

- Complete Python script with the slice template
- Topology diagram (ASCII art)
- Resource requirements summary (total cores, RAM, disk)
- Site availability check command
