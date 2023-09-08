import unittest

from fabrictestbed_extensions.fablib.node import Node
from fabrictestbed_extensions.fablib.slice import Slice


class HelloFabricTests(unittest.TestCase):
    """
    Run some basic tests against the testbed.
    """

    def test_fablib_hello(self, fablib, fabric_slice):
        """
        Create a slice with a single node, and echo a message from the node.
        """
        self.assertIsInstance(fabric_slice, Slice)

        # Add a node.
        node_name = "node-1"
        site_name = fablib.get_random_site()
        slice_name = fabric_slice.get_name()

        print(
            f"Adding node '{node_name}' at site '{site_name}' to slice '{slice_name}'.."
        )
        node = fabric_slice.add_node(name=node_name, site=site_name)

        self.assertIsInstance(node, Node)

        # Submit the slice.
        print(f"Submitting slice '{slice_name}'..")
        fabric_slice.submit()

        print(f"Slice '{slice_name}' status:")
        fabric_slice.show()

        print(f"Testing node '{node_name}' on slice '{slice_name}'...")

        for node in fabric_slice.get_nodes():
            stdout, stderr = node.execute("echo Hello, FABRIC from node `hostname -s`")

            self.assertEqual(stdout, f"Hello, FABRIC from node {node_name}\n")
            self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
