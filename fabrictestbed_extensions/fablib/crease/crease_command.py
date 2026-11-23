#!/usr/bin/env python3
"""Send Crease replay control commands to Crinkle monitors.

Runs on the analyzer node. Each command is sent as a raw IPv6 datagram with
next-header 254 to every monitor address given. The monitor's command parser
reads the payload directly after the fixed IPv6 header. Offsets are seconds
relative to this host's CLOCK_REALTIME, so this host and the monitors must
share a PTP domain.

Usage:
    crease_command.py record <start_offset> <end_offset> <ip> [<ip> ...]
    crease_command.py clear <ip> [<ip> ...]
    crease_command.py run <start_offset> <ip> [<ip> ...]
"""
import socket
import sys
import time

CREASE_PROT = 254
TYPE_REPLAY_RECORD = 1
TYPE_REPLAY_CLEAR = 2
TYPE_REPLAY_RUN = 4
S_TO_NS = 1_000_000_000

ARG_COUNTS = {"record": 2, "run": 1, "clear": 0}


def build_payload(cmd, now_ns, args):
    """The datagram payload for cmd, with args in seconds relative to now_ns."""
    if cmd == "record":
        start_ns = now_ns + int(float(args[0]) * S_TO_NS)
        end_ns = now_ns + int(float(args[1]) * S_TO_NS)
        return (
            bytes([TYPE_REPLAY_RECORD])
            + start_ns.to_bytes(8, "big")
            + end_ns.to_bytes(8, "big")
        )
    if cmd == "run":
        start_ns = now_ns + int(float(args[0]) * S_TO_NS)
        return bytes([TYPE_REPLAY_RUN]) + start_ns.to_bytes(8, "big")
    if cmd == "clear":
        return bytes([TYPE_REPLAY_CLEAR]) + b"\x00"
    raise ValueError(f"Unknown command: {cmd}")


def main(argv):
    """
    Send the command in argv to every monitor address it lists. Returns 0 if
    every send succeeded, 1 if any failed and 2 on a usage error.
    """
    if len(argv) < 2 or argv[0] not in ARG_COUNTS:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[0]
    n_args = ARG_COUNTS[cmd]
    cmd_args, ips = argv[1 : 1 + n_args], argv[1 + n_args :]
    if not ips:
        print("No monitor addresses given", file=sys.stderr)
        return 2
    payload = build_payload(cmd, time.time_ns(), cmd_args)
    sock = socket.socket(socket.AF_INET6, socket.SOCK_RAW, CREASE_PROT)
    failed = 0
    for ip in ips:
        try:
            sock.sendto(payload, (ip, 0))
        except OSError as e:
            failed += 1
            print(f"Sending {cmd} to {ip} failed: {e}", file=sys.stderr)
    print(f"Sent {cmd} to {len(ips) - failed} of {len(ips)} monitors")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
