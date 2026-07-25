# netinfo.py
#
# Copyright 2026 ZingyTomato
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import random
import socket
import struct


def _encode_dns_name(name):
    out = b""
    for label in name.split("."):
        out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def _decode_dns_name(data, offset):
    labels = []
    jumped = False
    resume_at = offset
    steps = 0
    while steps < 128:
        steps += 1
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                resume_at = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        labels.append(data[offset:offset + length].decode(errors="replace"))
        offset += length
    return ".".join(labels), (resume_at if jumped else offset)


def resolve_mdns_hostname(ip, timeout=0.4):
    """Query mDNS for the reverse (PTR) name of an IP. Returns hostname or None."""
    reversed_name = ".".join(reversed(ip.split("."))) + ".in-addr.arpa"
    txid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", txid, 0x0000, 1, 0, 0, 0)
    # Top bit of qclass set = "QU" (unicast-response) so we get a direct reply
    question = _encode_dns_name(reversed_name) + struct.pack(">HH", 12, 0x8001)
    packet = header + question

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, ("224.0.0.251", 5353))

        while True:
            data, addr = sock.recvfrom(4096)
            if addr[0] != ip:
                continue
            ancount = struct.unpack_from(">H", data, 6)[0]
            if ancount < 1:
                continue

            offset = 12
            _, offset = _decode_dns_name(data, offset)
            offset += 4  # qtype + qclass

            for _ in range(ancount):
                _, offset = _decode_dns_name(data, offset)
                rtype, _, _, rdlength = struct.unpack_from(">HHIH", data, offset)
                offset += 10
                if rtype == 12:  # PTR
                    name, _ = _decode_dns_name(data, offset)
                    return name.rstrip(".") or None
                offset += rdlength
    except Exception:
        return None
    finally:
        if sock:
            sock.close()


def _encode_netbios_query_name():
    raw = b"*" + b"\x00" * 15
    encoded = "".join(chr((b >> 4) + 0x41) + chr((b & 0xF) + 0x41) for b in raw)
    return bytes([32]) + encoded.encode() + b"\x00"


def resolve_netbios_name(ip, timeout=0.4):
    """Query NBNS (NetBIOS Node Status) for the host's name. Returns name or None."""
    txid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", txid, 0x0000, 1, 0, 0, 0)
    question = _encode_netbios_query_name() + struct.pack(">HH", 0x21, 0x01)
    packet = header + question

    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(packet, (ip, 137))
        data, _ = sock.recvfrom(4096)

        offset = 12
        _, offset = _decode_dns_name(data, offset)
        offset += 10  # type + class + ttl + rdlength
        num_names = data[offset]
        offset += 1

        fallback = None
        for _ in range(num_names):
            raw_name = data[offset:offset + 15]
            suffix = data[offset + 15]
            flags = struct.unpack_from(">H", data, offset + 16)[0]
            offset += 18

            name = raw_name.decode("ascii", errors="replace").strip()
            if not name or name == "*":
                continue
            is_group = bool(flags & 0x8000)
            if suffix == 0x00 and not is_group:
                return name
            if fallback is None:
                fallback = name
        return fallback
    except Exception:
        return None
    finally:
        if sock:
            sock.close()


def resolve_hostname(ip):
    """Best-effort hostname resolution: reverse DNS, then mDNS, then NetBIOS."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        pass

    name = resolve_mdns_hostname(ip)
    if name:
        return name

    return resolve_netbios_name(ip)


def read_arp_table():
    """Parse /proc/net/arp into an {ip: mac} map. Empty dict if unavailable."""
    entries = {}
    try:
        with open("/proc/net/arp") as f:
            lines = f.readlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue
            ip, mac = parts[0], parts[3]
            if mac and mac != "00:00:00:00:00:00":
                entries[ip] = mac
    except OSError:
        pass
    return entries
