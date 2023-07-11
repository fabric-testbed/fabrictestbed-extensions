import socket
import time

from fabrictestbed_extensions.fablib.fablib import FablibManager


def test_fablib_hello():
    fablib = FablibManager()

    fablib.show_config()

    # fablib.list_sites()

    # Give the slice a unique name so that slice creation will not
    # fail and we will know that it originated from an integration
    # test.
    time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    host = socket.gethostname()
    slice_name = f"integration test @ {time_stamp} on {host}"

    print(f"Creating slice '{slice_name}'..")
    slice = fablib.new_slice(name=slice_name)

    try:
        # Add a node.
        node = slice.add_node(name="node-1")

        # Submit the slice.
        slice.submit()

        slice.show()

        for node in slice.get_nodes():
            stdout, stderr = node.execute("echo Hello, FABRIC from node `hostname -s`")

    finally:
        slice.delete()
