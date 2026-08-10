#!/usr/bin/env python3
import enum
import getopt
import queue
import sys
import threading
from concurrent import futures
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address

from scapy.all import sniff
from scapy.fields import IntField, LongField, ShortField, XShortField
from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6, IPv6ExtHdrDestOpt
from scapy.layers.l2 import Ether
from scapy.packet import Packet, Raw, bind_layers

PROT_CMA = 254
CMA_ID = b"\x65\x87"


class CMA(Packet):
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
    ETHER_O = 0
    IPv6_O = 1
    CMA = 2
    ETHER_I = 3
    IP_I = 4
    PROT_I = 5
    RAW_I = 6


class Flow:
    def __init__(self, txport, rxport, ip_src, ip_dst, ip_prot, prot_sport, prot_dport):
        self.txport = txport
        self.rxport = rxport
        self.ip_src = ip_src
        self.ip_dst = ip_dst
        self.ip_prot = ip_prot
        self.prot_sport = prot_sport
        self.prot_dport = prot_dport

    def __hash__(self):
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
    while True:
        pkt = pkt_queue.get()
        if pkt is None:
            print("Worker exiting")
            break
        analyze_packet(pkt, monitors, output_queue)
        pkt_queue.task_done()


def writer_worker(output_queue: queue.Queue):
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
