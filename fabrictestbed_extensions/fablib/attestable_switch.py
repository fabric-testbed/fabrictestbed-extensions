#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2024 Illinois Institute of Technology
#
# This software was developed by Illinois Institute of Technology under NSF award 2346499 ("CREASE"),
# as part of the NSF CCRI-CISE (Community Research Infrastructure) program.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Nik Sultana

"""
Methods to work with `attestable switches`.

You would add a switch and operate on it like so::

    from fabrictestbed_extensions.fablib.fablib import FablibManager

    fablib = FablibManager()

    slice = fablib.new_slice(name="MySlice")
    s1 = slice.add_attestable_switch(name="s1", site=site, ports=["p0", "p1"])
    slice.submit();

    s1.start_switch()
    s1.run_command("show_ports")
    #s1.load_program("router.p4")
    s1.run_command("show_tables")
    s1.stop_switch()

    slice.delete()
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, List

from tabulate import tabulate

if TYPE_CHECKING:
    from fabrictestbed_extensions.fablib.slice import Slice

from fabrictestbed.slice_editor import Node as FimNode

from fabrictestbed_extensions.fablib.node import Node

log = logging.getLogger("fablib")


class Attestable_Switch(Node):
    """
    A class that abstracts programmable network elements (switches and NICs). These elements may be attestable -- that is, they provide runtime evidence about their configuration.
    """

    default_cores = 4
    default_ram = 8
    default_disk = 50
    default_image = "crease_ubuntu_22"
    default_username = "ubuntu"
    raw_image = "default_ubuntu_22"
    crease_path_prefix = "/home/ubuntu/.crease/"
    cfg_file = crease_path_prefix + "crease_switch_cfg.json"

    __version__ = "beta 3"
    __version_short__ = "b3"

    def __init__(
        self,
        slice: Slice,
        node: FimNode,
        validate: bool = False,
        raise_exception: bool = False,
        ports: List[str] = None,
        from_raw_image=False,
        setup_and_configure=True,
    ):
        """
        Attestable Switch constructor, usually invoked by ``Slice.add_attestable_switch()``.

        :param slice: same meaning as counterpart parameter for `Node`.
        :type slice: Slice

        :param node: same meaning as counterpart parameter for `Node`.
        :type node: Node

        :param validate: same meaning as counterpart parameter for `Node`.
        :type validate: bool

        :param raise_exception: same meaning as counterpart parameter for `Node`.
        :type raise_exception: bool

        :param ports: names of ports that the switch will have.
        :type ports: List[str]

        :param from_raw_image: start from a raw image and install all dependencies -- this takes longer.
        :type from_raw_image: bool

        :param setup_and_configure: set up and configure the attestable switch in post-boot config.
        :type setup_and_configure: bool
        """

        super().__init__(slice, node, validate, raise_exception)

        log.info(f"Creating Attestable Switch {self.get_name()}.")

        self.runtime_cfg = {}

        if None == self.get_switch_data(soft=False):
            log.info(
                f"Attestable Switch {Attestable_Switch.__version__} {self.get_name()}: (not found)"
            )

            assert len(ports) > 0

            self.cfg = {}
            self.cfg["ports"] = ports
            self.cfg["portmap"] = {}
            self.cfg["from_raw_image"] = from_raw_image
            self.cfg["setup_and_configure"] = setup_and_configure

            for port in ports:
                self.cfg["portmap"][port] = (
                    self.add_component(model="NIC_Basic", name=port)
                    .get_interfaces()[0]
                    .get_name()
                )
                log.info(f"Attestable Switch {self.get_name()}: added port {port}")

            self.set_switch_data(self.cfg)

        else:
            log.info(
                f"Attestable Switch {Attestable_Switch.__version__} {self.get_name()}: (found)"
            )
            self.cfg = self.get_switch_data(soft=False)

    def get_switch_data(self, soft=True):
        """
        Get switch-specific configuration data.
        """

        if soft:
            return self.cfg
        else:
            if "attestable_switch_config" in self.get_user_data():
                return self.get_user_data()["attestable_switch_config"]
            else:
                return None

    def set_switch_data(self, switch_data: dict):
        """
        Set switch-specific configuration data.
        """

        self.cfg = switch_data
        user_data = self.get_user_data()
        user_data["attestable_switch_config"] = switch_data
        self.set_user_data(user_data)

    def get_switch_config(self, k, quiet=True):
        """
        Get run-time configurable, switch-specific configuration data.
        """
        if not self.runtime_cfg:
            self.runtime_cfg = json.loads(
                self.execute(f"cat {Attestable_Switch.cfg_file}", quiet=quiet)[0]
            )
        val = self.runtime_cfg.get(k, None)
        if val == "False":
            return False
        elif val == "True":
            return True
        elif val == "None":
            return None
        return val

    def prep_switch_config_update(self, k, v):
        """
        Support function for commit_switch_config_update().
        """
        return k, str(v)

    def commit_switch_config_update(self, cfg_update):
        """
        Set run-time configurable, switch-specific configuration data.
        """
        if not self.runtime_cfg:
            self.runtime_cfg = json.loads(
                self.execute(f"cat {Attestable_Switch.cfg_file}", quiet=True)[0]
            )
        for k, v in cfg_update:
            self.runtime_cfg[k] = v
        s = f"echo '{json.dumps(self.runtime_cfg)}' > {Attestable_Switch.cfg_file}"
        self.execute(s, quiet=True)

    def get_port_names(self):
        """
        Get the port names of the switch.
        """

        return self.get_switch_data()["ports"]

    def get_port_interfaces(self):
        """
        Get the interface names of the switch's ports.
        """

        result = {}
        for port in self.get_switch_data()["portmap"].keys():
            result[port] = self.get_interface(
                name=self.get_switch_data()["portmap"][port]
            )
        return result

    def get_port_interface(self, port_name):
        """
        Get the interface name of a switch's port name.
        """

        return self.get_interface(name=self.get_switch_data()["portmap"][port_name])

    def get_port_device_listing(self, refresh: bool = False):
        """
        Get the name-to-interface mapping for a switch.
        :param refresh: Refresh the interface object with latest Fim info
        :type refresh: bool
        """

        mapping = {}
        for ifa in self.get_interfaces(refresh=refresh):
            mapping[ifa.get_component().get_short_name()] = ifa.get_device_name()
        result = []
        for port in self.get_port_names():
            result.append((port, mapping[port]))
        return result

    def __str__(self):
        """
        Creates a tabulated string describing the properties of the
        node.

        Intended for printing node information.

        :return: Tabulated string of node information
        :rtype: String
        """
        table = [
            ["ID", self.get_reservation_id()],
            ["Name", self.get_name()],
            ["Cores", self.get_cores()],
            ["RAM", self.get_ram()],
            ["Disk", self.get_disk()],
            ["Image", self.get_image()],
            ["Image Type", self.get_image_type()],
            ["Host", self.get_host()],
            ["Site", self.get_site()],
            ["Management IP", self.get_management_ip()],
            ["Reservation State", self.get_reservation_state()],
            ["Error Message", self.get_error_message()],
            ["SSH Command", self.get_ssh_command()],
            ["Ports", str(self.get_port_names())],
        ]

        return tabulate(table)  # , headers=["Property", "Value"])

    @staticmethod
    def name(orig_name):
        """
        Devise a consistent naming prefix for switches.
        """

        assert orig_name is not None
        as_name_prefix = (
            "attestable_switch_" + Attestable_Switch.__version_short__ + "_"
        )
        result = orig_name
        if not orig_name.startswith(as_name_prefix):
            result = as_name_prefix + orig_name
        return result

    def get_name(self) -> str or None:
        """
        Gets the name of the FABRIC node.

        :return: the name of the node
        :rtype: String
        """
        try:
            return Attestable_Switch.name(self.get_fim_node().name)
        except:
            return None

    @staticmethod
    def new_attestable_switch(
        slice: Slice = None,
        name: str = None,
        site: str = None,
        avoid: List[str] = [],
        validate: bool = False,
        raise_exception: bool = False,
        ports: List[str] = None,
        from_raw_image=False,
        setup_and_configure=True,
    ):
        """
        Not intended for API call.  See: Slice.add_attestable_switch()

        Creates a new attestable switch.

        :param slice: the fablib slice to build the new node on
        :type slice: Slice

        :param name: the name of the new node
        :type name: str

        :param site: the name of the site to build the node on
        :type site: str

        :param avoid: a list of node names to avoid
        :type avoid: List[str]

        :param validate: Validate node can be allocated w.r.t available resources
        :type validate: bool

        :param raise_exception: Raise exception in case validation failes
        :type raise_exception: bool

        :param ports: names of ports that the switch will have.
        :type ports: List[str]

        :param from_raw_image: start from a raw image and install all dependencies -- this takes longer.
        :type from_raw_image: bool

        :param setup_and_configure: set up and configure the attestable switch in post-boot config.
        :type setup_and_configure: bool

        :return: a new fablib Attestable_Switch
        :rtype: Attestable_Switch
        """
        if site is None:
            [site] = slice.get_fablib_manager().get_random_sites(avoid=avoid)

        name = Attestable_Switch.name(name)

        log.info(
            f"Adding attestable switch: {name}, slice: {slice.get_name()}, site: {site}, ports: "
            f"{ports}, from_raw_image: {from_raw_image}, setup_and_configure: {setup_and_configure}"
        )
        node = Attestable_Switch(
            slice,
            slice.topology.add_node(name=name, site=site),
            validate=validate,
            raise_exception=raise_exception,
            ports=ports,
            from_raw_image=from_raw_image,
            setup_and_configure=setup_and_configure,
        )
        node.set_capacities(
            cores=Node.default_cores, ram=Node.default_ram, disk=Node.default_disk
        )

        node.set_image(
            Attestable_Switch.default_image, username=Attestable_Switch.default_username
        )

        node.init_fablib_data()

        return node

    @staticmethod
    def get_attestable_switch(slice: Slice = None, node=None):
        """
        Returns a fresh reference to a switch using existing FABRIC resources.
        """

        return Attestable_Switch(slice, node)

    @staticmethod
    def get_pretty_name_dict():
        """
        Return mappings from non-pretty names to pretty names.

        Pretty names are in table headers.
        """

        r = Node.get_pretty_name_dict()
        r["ports"] = "Switch ports"
        return r

    def toDict(self, skip=[]):
        """
        Returns the node attributes as a dictionary

        :return: slice attributes as dictionary
        :rtype: dict
        """
        rtn_dict = super().toDict(skip)
        if "ports" not in skip:
            rtn_dict["ports"] = str(self.get_port_names())

        return rtn_dict

    def switch_config(self, log_dir="."):
        """
        Post-boot configuration for the switch.
        """

        from_raw_image = self.get_switch_data()["from_raw_image"]

        if self.get_switch_data()["setup_and_configure"]:
            self.execute(f'echo "{"{}"}" > {Attestable_Switch.cfg_file}')

            log.info(
                f"Attestable Switch {self.get_name()}: starting config. from_raw_image={from_raw_image}"
            )

            if not from_raw_image:
                log.info(
                    f"Image already contains Attestable Switch: skipping compilation."
                )
            else:
                print(f"Compiling Attestable Switch {self.get_name()}, ", end="")
                start = time.time()
                log.info(f"Attestable Switch {self.get_name()}: cloning repo...")
                self.execute(
                    'bash -c "git clone https://github.com/awolosewicz/bmv2-remote-attestation.git"',
                    quiet=True,
                )
                self.execute(
                    'bash -c "cd ~/bmv2-remote-attestation && git checkout stable"',
                    quiet=True,
                )
                log.info(
                    f"Attestable Switch {self.get_name()}: obtaining dependencies..."
                )

                self.execute(
                    "bash -c 'source /etc/lsb-release && echo \"deb http://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${DISTRIB_RELEASE}/ /\" | sudo tee /etc/apt/sources.list.d/home:p4lang.list'",
                    quiet=True,
                )
                self.execute(
                    "bash -c 'source /etc/lsb-release && curl -fsSL https://download.opensuse.org/repositories/home:p4lang/xUbuntu_${DISTRIB_RELEASE}/Release.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/home_p4lang.gpg > /dev/null'",
                    quiet=True,
                )

                self.execute(
                    'bash -c "sudo apt-get update && sudo apt-get install -y p4lang-p4c net-tools python3-scapy"',
                    quiet=True,
                )
                log.info(
                    f"Attestable Switch {self.get_name()}: starting compilation..."
                )
                self.execute(
                    'bash -c "cd ~/bmv2-remote-attestation/ && ./install_deps.sh && ./autogen.sh && ./configure && make -j 4 && sudo make install"',
                    quiet=True,
                )
                self.execute(
                    'bash -c "sudo rm /usr/bin/simple_switch /usr/bin/simple_switch_CLI && sudo rm -rf /home/ubuntu/bmv2-remote-attestation && sudo ldconfig"',
                    quiet=True,
                )
                log.info(f"Attestable Switch {self.get_name()}: finished compilation")
                print(f"Done! ({time.time() - start:.0f} sec)")

            nothing_p4 = """#include <core.p4>
#include <v1model.p4>

struct metadata {}
struct headers {}

parser DuffParser(packet_in packet,
                  out headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
  state start {
    transition accept;
  }
}

control DuffVerifyChecksum(inout headers hdr,
                           inout metadata meta) {
  apply {}
}

control DuffIngress(inout headers hdr,
                    inout metadata meta,
                    inout standard_metadata_t standard_metadata) {
  apply {}
}

control DuffEgress(inout headers hdr,
                   inout metadata meta,
                   inout standard_metadata_t standard_metadata) {
  apply {}
}

control DuffComputeChecksum(inout headers  hdr,
                            inout metadata meta) {
  apply {}
}

control DuffDeparser(packet_out packet, in headers hdr) {
  apply {}
}

V1Switch(
  DuffParser(),
  DuffVerifyChecksum(),
  DuffIngress(),
  DuffEgress(),
  DuffComputeChecksum(),
  DuffDeparser()
) main;"""

            print(f"Setting up Attestable Switch {self.get_name()}, ", end="")
            start = time.time()

            self.execute("sudo sysctl net.ipv4.ip_forward=1", quiet=True)

            self.execute(
                f"echo '{nothing_p4}' > {Attestable_Switch.crease_path_prefix}nothing.p4"
            )

            for port in self.get_port_names():
                for (
                    ifa
                ) in (
                    self.get_interfaces()
                ):  # FIXME inefficient code -- use a look-up instead of looping.
                    if ifa.get_component().get_short_name() == port:
                        self.execute(
                            f"sudo ip link set dev {ifa.get_device_name()} up",
                            quiet=True,
                        )
                        self.execute(
                            f"sudo ip link set dev {ifa.get_device_name()} arp off"
                        )

            # self.execute(f"sudo ip route del 0/0")
            log.info(f"Attestable Switch {self.get_name()}: finished config")
            print(f"Done! ({time.time() - start:.0f} sec)")
        else:
            log.info(f"Attestable Switch {self.get_name()}: skipping setup and config")

    def check(self, quiet=True):
        """
        Check whether the switch was initialised correctly.
        """

        result = True

        (out, _) = self.execute("sudo sysctl net.ipv4.ip_forward", quiet=True)
        check = out == "net.ipv4.ip_forward = 1\n"
        if not check:
            log.error(f"Attestable Switch {self.get_name()}: failed check 1")
            if not quiet:
                print(f"Attestable Switch {self.get_name()}: failed check 1")

        result = result and check

        (out, _) = self.execute(
            f"ls -s {Attestable_Switch.crease_path_prefix}nothing.p4", quiet=True
        )
        check = out == f"4 {Attestable_Switch.crease_path_prefix}nothing.p4\n"
        if not check:
            log.error(f"Attestable Switch {self.get_name()}: failed check 2")
            if not quiet:
                print(f"Attestable Switch {self.get_name()}: failed check 2")

        result = result and check

        return result

    def start_switch(
        self,
        program="/home/ubuntu/.crease/nothing.json",
        dry=False,
        quiet=True,
        force=False,
        with_RA=False,
        RA_port=None,
        RA_et=None,
        with_SPADE=False,
        SPADE_file=None,
        SPADE_switch_id=None,
        SPADE_verbosity=None,
        SPADE_period=None,
        disable_RA_broadcast=False,
        timeout=2,
    ):
        """
        Start the switch executing, and have it run a P4 program.
        """

        if not force and self.get_switch_config("Running"):
            print("Switch already running")
            return False

        port_sequence = ""
        port_num = 0
        for _, port_device in self.get_port_device_listing():
            port_sequence += f"-i {str(port_num)}@{port_device} "
            port_num += 1

        cfg_update = []

        RA_inclusion = ""
        cfg_update.append(self.prep_switch_config_update("with_RA", False))

        if with_RA:
            RA_inclusion = "--enable-ra"
            cfg_update.append(self.prep_switch_config_update("with_RA", True))

        if RA_port is not None:
            assert with_RA
            cfg_update.append(self.prep_switch_config_update("RA_port", RA_port))
            RA_inclusion += " --ra-port " + str(RA_port)
        else:
            cfg_update.append(self.prep_switch_config_update("RA_port", None))

        if RA_et is not None:
            assert with_RA
            cfg_update.append(self.prep_switch_config_update("RA_et", RA_et))
            RA_inclusion += " --ra-etype " + str(RA_et)
        else:
            cfg_update.append(self.prep_switch_config_update("RA_et", None))

        if disable_RA_broadcast:
            assert with_RA
            cfg_update.append(
                self.prep_switch_config_update(
                    "disable_RA_broadcast", disable_RA_broadcast
                )
            )
            RA_inclusion += " --disable-ra-broadcast"
        else:
            cfg_update.append(
                self.prep_switch_config_update("disable_RA_broadcast", False)
            )

        if with_SPADE:
            RA_inclusion += " --enable-spade"
            cfg_update.append(self.prep_switch_config_update("with_SPADE", True))
        else:
            cfg_update.append(self.prep_switch_config_update("with_SPADE", False))

        if SPADE_file is not None:
            assert with_SPADE
            cfg_update.append(self.prep_switch_config_update("SPADE_file", SPADE_file))
            RA_inclusion += " --spade-file " + str(SPADE_file)
        else:
            cfg_update.append(self.prep_switch_config_update("SPADE_file", None))

        if SPADE_switch_id is not None:
            assert with_SPADE
            cfg_update.append(
                self.prep_switch_config_update("SPADE_switch_id", SPADE_switch_id)
            )
            RA_inclusion += " --spade-switch-id " + str(SPADE_switch_id)
        else:
            cfg_update.append(self.prep_switch_config_update("SPADE_switch_id", None))

        if SPADE_verbosity is not None:
            assert with_SPADE
            cfg_update.append(
                self.prep_switch_config_update("SPADE_verbosity", SPADE_verbosity)
            )
            RA_inclusion += " --spade-verbosity " + str(SPADE_verbosity)
        else:
            cfg_update.append(self.prep_switch_config_update("SPADE_verbosity", None))

        if SPADE_period is not None:
            assert with_SPADE
            cfg_update.append(
                self.prep_switch_config_update("SPADE_period", SPADE_period)
            )
            RA_inclusion += " --spade-period " + str(SPADE_period)
        else:
            cfg_update.append(self.prep_switch_config_update("SPADE_period", None))

        commands = [
            f"[ ! -f {Attestable_Switch.crease_path_prefix}nothing.json ] && cd {Attestable_Switch.crease_path_prefix} && p4c --target bmv2 --arch v1model {Attestable_Switch.crease_path_prefix}nothing.p4",
            f"sudo simple_switch {port_sequence} {program} --log-file ~/switch.log --log-flush -- --enable-swap {RA_inclusion}",
        ]

        stdout = []
        stderr = []
        if dry:
            for command in commands:
                print(command)
        else:
            (out, err) = self.execute(commands[0], quiet=quiet)
            stdout.append(out)
            stderr.append(err)
            job = self.execute_thread(commands[1])
            time.sleep(timeout)
            if not job.running() and not quiet:
                (out, err) = job.result()
                stdout.append(out)
                stderr.append(err)

        stdout = list(filter(lambda line: line != "", stdout))
        stderr = list(filter(lambda line: line != "", stderr))

        if not quiet:
            print("stdout: " + str(stdout))
            print("stderr: " + str(stderr))

        result = None

        if stderr:
            result = False
        else:
            cfg_update.append(self.prep_switch_config_update("Running", True))
            result = True

        self.commit_switch_config_update(cfg_update)

        return result

    def stop_switch(self, dry=False, quiet=True, force=False):
        """
        Stop the switch from executing.
        """

        if not force and not self.get_switch_config("Running"):
            print("Switch not running")
            return False

        command = "sudo killall simple_switch"

        cfg_update = []

        stdout = []
        stderr = []
        if dry:
            print(command)
        else:
            (out, err) = self.execute(command, quiet=quiet)
            stdout.append(out)
            stderr.append(err)

        stdout = list(filter(lambda line: line != "", stdout))
        stderr = list(filter(lambda line: line != "", stderr))

        if not quiet:
            print("stdout: " + str(stdout))
            print("stderr: " + str(stderr))

        result = None

        if stderr and not force:
            result = False
        else:
            cfg_update.append(self.prep_switch_config_update("Running", False))
            result = True

        self.commit_switch_config_update(cfg_update)

        return result

    def load_program(self, filename, dry=False, quiet=True):
        """
        Runtime update of a P4 program on a running switch.
        """

        output_file = os.path.splitext(os.path.basename(filename))[0] + ".json"
        commands = [
            f"p4c --target bmv2 --arch v1model ~/{os.path.basename(filename)}",
            f'echo "load_new_config_file {output_file}" | simple_switch_CLI',
            f'echo "swap_configs" | simple_switch_CLI',
        ]

        stdout = []
        stderr = []
        if dry:
            for command in commands:
                print(command)
        else:
            self.upload_file(filename, os.path.basename(filename), retry=1)
            for command in commands:
                (out, err) = self.execute(command, quiet=quiet)
                stdout.append(out)
                stderr.append(err)

        stderr = list(filter(lambda line: line != "", stderr))

        if stderr:
            return False
        else:
            return True

    def run_command(self, cmd, dry=False, quiet=False):
        """
        Run a CLI command on the switch.
        """

        command = f"echo '{cmd}' | simple_switch_CLI"

        stdout = []
        stderr = []

        if dry:
            print(command)
        else:
            (out, err) = self.execute(command, quiet=quiet)
            stdout.append(out)
            stderr.append(err)

        for out in stdout:
            for line in out.split("\n"):
                if "RuntimeCmd: Error" in line:
                    return False

        stderr = list(filter(lambda line: line != "", stderr))

        if stderr:
            return False
        else:
            return True

    def get_switch_features(self):
        """
        Get feature information from the switch.
        """
        result = {"Running": self.get_switch_config("Running")}
        if self.get_switch_config("Running"):
            result["with_RA"] = self.get_switch_config("with_RA")
            if self.get_switch_config("with_RA"):
                if self.get_switch_config("RA_port") is not None:
                    result["RA_port"] = self.get_switch_config("RA_port")
                if self.get_switch_config("RA_et") is not None:
                    result["RA_et"] = self.get_switch_config("RA_et")
                if self.get_switch_config("disable_RA_broadcast"):
                    result["disable_RA_broadcast"] = self.get_switch_config(
                        "disable_RA_broadcast"
                    )
            result["with_SPADE"] = self.get_switch_config("with_SPADE")
            if self.get_switch_config("with_SPADE"):
                if self.get_switch_config("SPADE_file") is not None:
                    result["SPADE_file"] = self.get_switch_config("SPADE_file")
                if self.get_switch_config("SPADE_switch_id") is not None:
                    result["SPADE_switch_id"] = self.get_switch_config(
                        "SPADE_switch_id"
                    )
                if self.get_switch_config("SPADE_verbosity") is not None:
                    result["SPADE_verbosity"] = self.get_switch_config(
                        "SPADE_verbosity"
                    )
                if self.get_switch_config("SPADE_period") is not None:
                    result["SPADE_period"] = self.get_switch_config("SPADE_period")

        return result

    def get_version(self):
        """
        Get version information from the switch.
        """

        commands = [
            f"simple_switch -v",
        ]

        stdout = []
        stderr = []

        for command in commands:
            (out, err) = self.execute(command, quiet=False)
            stdout.append(out)
            stderr.append(err)

        stderr = list(filter(lambda line: line != "", stderr))

        if stderr:
            return False
        else:
            print(str(self.get_switch_features()))
            return True
