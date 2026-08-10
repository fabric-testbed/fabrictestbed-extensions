# Generate Usage Example

Create a working code example demonstrating a FABlib feature.

## Arguments

$ARGUMENTS - The feature or workflow to demonstrate. Examples:
- "create a slice with GPU nodes"
- "set up L2 network between two sites"
- "mount CephFS storage"
- "use the CLI to list resources"
- "configure FABNetv4Ext for internet access"

## Instructions

1. Identify which FABlib classes and methods are involved.

2. Read the relevant source code to understand:
   - Required parameters and their types
   - Default values
   - Common error scenarios
   - Return values

3. Write a complete, self-contained example that:
   - Imports all necessary modules
   - Includes comments explaining each step
   - Uses realistic parameter values (real site names, valid component models)
   - Handles errors gracefully
   - Includes cleanup (slice.delete())
   - Works as both a script and in Jupyter

4. Reference the Constants class for valid values:
   - Site names from `fablib.list_sites()`
   - Component models from Constants (NIC_Basic, GPU_TeslaT4, etc.)
   - Network types (L2Bridge, L2PTP, FABNetv4, etc.)
   - Image names from Constants.IMAGE_NAMES

5. Add optional enhancements:
   - Topology visualization with `slice.show()`
   - Status checking with `slice.isStable()`
   - SSH execution examples

## Output

A complete Python code block with:
- Docstring at the top explaining what the example demonstrates
- Step-by-step comments
- Error handling
- Resource cleanup
- Expected output description
