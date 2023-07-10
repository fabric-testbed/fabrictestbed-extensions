from fabrictestbed_extensions.fablib.fablib import FablibManager


def test_fablib_hello():
    fablib = FablibManager()

    fablib.show_config()

    fablib.list_sites()

    slice = fablib.new_slice(name="MySlice")

    # Add a node.
    node = slice.add_node(name="Node1")

    # Submit the slice.
    slice.submit()

    slice.show()

    for node in slice.get_nodes():
        stdout, stderr = node.execute("echo Hello, FABRIC from node `hostname -s`")

    slice.delete()
