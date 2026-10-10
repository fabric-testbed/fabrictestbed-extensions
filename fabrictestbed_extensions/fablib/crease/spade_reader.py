#!/usr/bin/env python3
"""Standalone packet-sniffing script, uploaded to and run on the Crinkle analyzer
node, that parses incoming CMA-tagged packets and converts them into SPADE
provenance records written to the spade_pipe named pipe for SPADE's DSL reporter.
"""
import enum
import getopt
import queue
import sys
import threading
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from scapy.all import sniff
from scapy.fields import IntField, LongField, ShortField, XShortField
from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether
from scapy.packet import Packet, bind_layers

PROT_CMA = 254
CMA_ID = b"\x65\x87"


class CMA(Packet):
    """Scapy packet definition for the CMA trailer that Crinkle monitors append to
    captured packets, carrying the monitor id, receiving port, receive timestamp,
    and the sender-assigned unique packet id fields used to correlate a packet
    across hops.
    """

    name = "CMA"
    fields_desc = [
        ShortField("len", 0),
        LongField("rx_time", 0),
        ShortField("mon_id", 0),
        ShortField("rx_port_id", 0),
        IntField("res", 0),
        LongField("uid_time", 0),
        ShortField("uid_mon", 0),
        ShortField("uid_port", 0),
        ShortField("time_chk", 0),
        XShortField("cma", CMA_ID),
    ]


class PktLayers(enum.IntEnum):
    """Named indices into the layered structure of a captured CMA packet (the outer
    Ethernet/IPv6 headers, the CMA trailer, and the tunneled inner Ethernet/IP/
    protocol/payload); currently unused by this script.
    """

    ETHER_O = 0
    IPv6_O = 1
    CMA = 2
    ETHER_I = 3
    IP_I = 4
    PROT_I = 5
    RAW_I = 6


class Flow:
    """A hashable 5-tuple-like key (TX/RX ports plus IP/transport addressing)
    identifying one network flow, used to assign and look up a stable SPADE
    artifact id per flow.
    """

    def __init__(self, txport, rxport, ip_src, ip_dst, ip_prot, prot_sport, prot_dport):
        """
        Store the flow's TX/RX port identifiers and IP/transport addressing used to
        uniquely identify it.

        :param txport: identifier of the port the packet was retransmitted out of
        :param rxport: identifier of the port the packet was received on
        :param ip_src: source IP address of the flow
        :param ip_dst: destination IP address of the flow
        :param ip_prot: IP protocol number (e.g. 6 for TCP, 17 for UDP)
        :param prot_sport: transport-layer source port, if applicable
        :param prot_dport: transport-layer destination port, if applicable
        """
        self.txport = txport
        self.rxport = rxport
        self.ip_src = ip_src
        self.ip_dst = ip_dst
        self.ip_prot = ip_prot
        self.prot_sport = prot_sport
        self.prot_dport = prot_dport

    def __hash__(self):
        """Hash the flow by its full field tuple, so equal flows map to the same dict key."""
        return hash(
            (
                self.txport,
                self.rxport,
                self.ip_src,
                self.ip_dst,
                self.ip_prot,
                self.prot_sport,
                self.prot_dport,
            )
        )

    def __eq__(self, other):
        """Compare two flows for equality by their full field tuple."""
        return (
            self.txport,
            self.rxport,
            self.ip_src,
            self.ip_dst,
            self.ip_prot,
            self.prot_sport,
            self.prot_dport,
        ) == (
            other.txport,
            other.rxport,
            other.ip_src,
            other.ip_dst,
            other.ip_prot,
            other.prot_sport,
            other.prot_dport,
        )


bind_layers(IPv6, CMA, nh=PROT_CMA)
bind_layers(CMA, Ether)
flowptr = 0
flows = {}


def analyze_packet(
    pkt: Packet,
    monitors: dict[int, dict[int, tuple[str, str]]],
    output_queue: queue.Queue,
):
    """
    Parse one sniffed packet for a CMA trailer and, if present, convert it into
    SPADE provenance lines: an "Artifact" vertex the first time a flow is seen,
    plus "Used"/"WasGeneratedBy" edges recording this packet's receipt and
    retransmission across the hop. The resulting lines are pushed onto
    output_queue for the writer thread to persist. Packets without a CMA trailer
    produce no lines.

    :param pkt: the packet captured by scapy's sniff()
    :type pkt: Packet
    :param monitors: maps a monitor id to a mapping of its port id (1 or 2) to
        that port's SPADE interface identifier, used to resolve the packet's
        TX/RX port names
    :type monitors: dict[int, dict[int, tuple[str, str]]]
    :param output_queue: queue the generated SPADE lines are pushed onto for the
        writer thread to persist
    :type output_queue: queue.Queue
    """
    global flowptr
    global flows
    size = None
    monitor_id = None
    monitor_iface_id = None
    uid = None
    eth_src = None
    eth_dst = None
    eth_type = None
    ip_ver = None
    ip_src = None
    ip_dst = None
    ip_prot = None
    prot_sport = None
    prot_dport = None
    time = None
    output_lines = []

    if CMA in pkt:
        print("Received packet")
        base = pkt["CMA"]
        monitor_id = base.mon_id
        monitor_iface_id = base.rx_port_id
        uid = f"{base.uid_mon}-{base.uid_port}-{base.uid_time}"
        size = base.len - 16
        epoch = base.rx_time / 1e9
        time = datetime.fromtimestamp(epoch).strftime("%Y-%m-%d_%H:%M:%S.%f")

        h_eth = base["Ether"]
        eth_type = hex(h_eth.type)
        h_ip = None
        if IP in base:
            h_ip = base["IP"]
            ip_src = IPv4Address(h_ip.src)
            ip_dst = IPv4Address(h_ip.dst)
            ip_prot = h_ip.proto
        elif IPv6 in base:
            h_ip = base["IPv6"]
            ip_src = IPv6Address(h_ip.src)
            ip_dst = IPv6Address(h_ip.dst)
            ip_prot = h_ip.nh
        if ip_prot == 6:
            h_tcp = h_ip["TCP"]
            prot_sport = h_tcp.sport
            prot_dport = h_tcp.dport
        elif ip_prot == 17:
            h_tcp = h_ip["UDP"]
            prot_sport = h_tcp.sport
            prot_dport = h_tcp.dport

        tx_id = None
        rx_id = None
        if monitor_iface_id == 1:
            tx_id = 1
            rx_id = 2
        else:
            tx_id = 2
            rx_id = 1
        tx_port = monitors[monitor_id][tx_id]
        rx_port = monitors[monitor_id][rx_id]
        thisflow = Flow(
            tx_port, rx_port, ip_src, ip_dst, ip_prot, prot_sport, prot_dport
        )
        flowhash = hash(thisflow)
        fid = None
        if flowhash in flows:
            fid = flows[flowhash]
            # print(f'Previous flow {fid}')
        else:
            fid = flowptr
            flowptr += 1
            flows[flowhash] = fid
            # print(f'New flow {fid}')
            # print(f'type:Artifact id:{fid} eth.type:{eth_type} ip.src:{ip_src} ip.dst:{ip_dst} ip.prot:{ip_prot} prot.sport:{prot_sport} prot.dport:{prot_dport}\n')
            output_lines.append(
                f"type:Artifact id:{fid} eth.type:{eth_type} ip.src:{ip_src} ip.dst:{ip_dst} ip.prot:{ip_prot} prot.sport:{prot_sport} prot.dport:{prot_dport}\n"
            )
        # print('Writing spade edges')
        print(
            f"type:Used from:{rx_port} to:{fid} pkt_id:{uid} size:{size} time:{time} epoch:{epoch}\n"
        )
        output_lines.append(
            f"type:Used from:{rx_port} to:{fid} pkt_id:{uid} size:{size} time:{time} epoch:{epoch}\n"
        )
        print(
            f"type:WasGeneratedBy from:{fid} to:{tx_port} pkt_id:{uid} size:{size} time:{time} epoch:{epoch}\n"
        )
        output_lines.append(
            f"type:WasGeneratedBy from:{fid} to:{tx_port} pkt_id:{uid} size:{size} time:{time} epoch:{epoch}\n"
        )

    # ...rest of analysis...
    output_queue.put(output_lines)


def packet_worker(pkt_queue: queue.Queue, monitors, output_queue: queue.Queue):
    """
    Continuously pull packets from pkt_queue and analyze them until a None
    sentinel is received, then exit the worker thread.

    :param pkt_queue: queue of sniffed packets awaiting analysis
    :type pkt_queue: queue.Queue
    :param monitors: maps monitor id to its port-id-to-interface-name mapping,
        passed through to analyze_packet()
    :param output_queue: queue the generated SPADE lines are pushed onto for the
        writer thread to persist
    :type output_queue: queue.Queue
    """
    while True:
        pkt = pkt_queue.get()
        if pkt is None:
            print("Worker exiting")
            break
        analyze_packet(pkt, monitors, output_queue)
        pkt_queue.task_done()


def writer_worker(output_queue: queue.Queue):
    """
    Open the spade_pipe named pipe and write each batch of SPADE lines pulled from
    output_queue to it, flushing after every batch, until a None sentinel is
    received.

    :param output_queue: queue of line lists produced by the analysis workers
    :type output_queue: queue.Queue
    """
    with open("spade_pipe", "w") as pipe:
        while True:
            lines = output_queue.get()
            if lines is None:
                print("Writer exiting")
                break
            for line in lines:
                pipe.write(line)
            pipe.flush()
            output_queue.task_done()


if __name__ == "__main__":

    optpairs, args = getopt.getopt(sys.argv[1:], "m")
    monitors = {}
    ana_iface = ""
    pkt_queue = queue.Queue()
    output_queue = queue.Queue()
    ana_iface = args[0]
    num_workers = int(args[1])
    idx = 2
    id = -1
    output_lines = []
    while idx < len(args):
        iface_parts = args[idx].split("@", 1)
        if len(iface_parts) == 1:
            id = args[idx]
            monitors[int(id)] = {}
        else:
            iface_id = iface_parts[0]
            node = iface_parts[1].split("-", 1)[0]
            print(f"type:Agent id:{node}\n")
            output_lines.append(f"type:Agent id:{node}\n")
            print(f"type:Process id:{iface_parts[1]}\n")
            output_lines.append(f"type:Process id:{iface_parts[1]}\n")
            print(f"type:WasControlledBy from:{iface_parts[1]} to:{node}\n")
            output_lines.append(
                f"type:WasControlledBy from:{iface_parts[1]} to:{node}\n"
            )
            monitors[int(id)][int(iface_id)] = iface_parts[1]
        idx += 1
    output_queue.put(output_lines)
    print(monitors)
    print(ana_iface)
    # sniff(prn=lambda x: analyze_packet(x, monitors), iface=ana_iface)
    workers = []
    writer = threading.Thread(target=writer_worker, args=(output_queue,))
    writer.daemon = True
    writer.start()
    for _ in range(num_workers - 1):
        t = threading.Thread(
            target=packet_worker, args=(pkt_queue, monitors, output_queue)
        )
        t.daemon = True
        t.start()
        workers.append(t)

    def enqueue_packet(pkt):
        """
        Callback passed to scapy's sniff() that queues each captured packet for
        asynchronous analysis by the worker threads.

        :param pkt: the packet captured by sniff()
        """
        pkt_queue.put(pkt)

    sniff(prn=enqueue_packet, iface=ana_iface)

    pkt_queue.join()
    for _ in workers:
        pkt_queue.put(None)
    for t in workers:
        t.join()

    output_queue.join()
    output_queue.put(None)
    writer.join()
