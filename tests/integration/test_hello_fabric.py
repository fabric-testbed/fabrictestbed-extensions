import socket
import time
import unittest

from fabrictestbed_extensions.fablib.fablib import FablibManager
from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.slice import Slice


class HelloFabricTests(unittest.TestCase):
    """
    Run some basic tests against the testbed.
    """

    def test_fablib_hello(self):
        """
        Create a slice with a single node, and echo a message from the node.
        """
        fablib = FablibManager()

        fablib.show_config()

        # fablib.list_sites()

        # Give the slice a unique name so that slice creation will not
        # fail (because there is an existing slice with the same name) and
        # we will have some hints about the test that created the slice.
        time_stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        host = socket.gethostname()
        slice_name = f"integration test @ {time_stamp} on {host}"

        print(f"Creating slice '{slice_name}'..")
        slice = fablib.new_slice(name=slice_name)

        self.assertIsInstance(slice, Slice)

        try:
            # Add a node.
            node_name = "node-1"
            site_name = fablib.get_random_site()

            print(
                f"Adding node '{node_name}' at site '{site_name}' to slice '{slice_name}'.."
            )
            node = slice.add_node(name=node_name, site=site_name)

            self.assertIsInstance(node, Node)

            # Submit the slice.
            print(f"Submitting slice '{slice_name}'..")
            slice.submit()

            print(f"Slice '{slice_name}' status:")
            slice.show()

            print(f"Testing node '{node_name}' on slice '{slice_name}'...")
            for node in slice.get_nodes():
                stdout, stderr = node.execute(
                    "echo Hello, FABRIC from node `hostname -s`"
                )

                self.assertEqual(stdout, f"Hello, FABRIC from node {node_name}\n")
                self.assertEqual(stderr, "")

        finally:
            slice.delete()


if __name__ == "__main__":
    unittest.main()
