# scanner.py
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

import threading
import ipaddress
import socket
import struct
import nmap
from concurrent.futures import ThreadPoolExecutor
from gi.repository import GLib

from . import netinfo

class NetworkScanner:
    """Network scanning functionality"""

    # Map of known service ports to service identifiers.
    # Only includes ports that are distinctive enough for a reliable guess.
    SERVICE_PORTS = {
        139: "smb",
        445: "smb",
        9090: "cockpit",
        3306: "mysql",
        5432: "postgresql",
        6379: "redis",
        8123: "homeassistant",
        32400: "plex",
        631: "cups",
        27017: "mongodb",
        8006: "proxmox",
        5001: "synology",
    }

    def __init__(self):
        self.common_ports = [22, 80, 443, 3389, 53, 21, 23, 8080, 8443, 8006, 5000, 5001, 445, 139, 9090, 3000, 3306, 5432, 6379, 8123, 32400, 9000, 631, 27017]
        self.is_scanning = False
        self._scan_generation = 0
        self.hosts_scanned = 0
        self.total_hosts = 0
        self.partial_results = []
        self.lock = threading.Lock()

        self.max_workers = 100

    def set_max_workers(self, count):
        """Set the maximum number of worker threads"""
        if 1 <= count <= 500:
            self.max_workers = count
        else:
            print(_("Thread count must be between 1 and 500"))

    def validate_ip_range(self, ip_range):
        if not ip_range:
            return False, _("Please enter an IP range")

        try:
            if '/' in ip_range or '-' in ip_range:
                pass
            else:
                ipaddress.IPv4Address(ip_range)
            return True, _("Valid IP range")
        except Exception as e:
            return False, _("Invalid IP range: {e}").format(e=e)

    def parse_ip_range_for_list(self, ip_range):
        hosts = []
        try:
            if '/' in ip_range:
                net = ipaddress.ip_network(ip_range, strict=False)
                hosts = list(net.hosts())
            elif '-' in ip_range:
                base_ip, range_part = ip_range.rsplit('-', 1)
                base_parts = base_ip.split('.')

                if len(base_parts) == 4:
                    base_network = '.'.join(base_parts[:3])
                    start_ip = int(base_parts[3])
                    end_ip = int(range_part)
                elif len(base_parts) == 3:
                    base_network = base_ip
                    start_ip = 1
                    end_ip = int(range_part)
                else:
                    raise ValueError(_("Invalid range format!"))

                hosts = [ipaddress.IPv4Address(f"{base_network}.{i}") for i in range(start_ip, end_ip + 1)]
            else:
                hosts = [ipaddress.IPv4Address(ip_range)]
        except Exception as e:
            print(_("Error parsing IP range: {e}").format(e=e))
            hosts = []
        return hosts

    def scan_single_ip(self, host, devices, progress_callback=None, deep_scan=False, generation=None):
        if not self.is_scanning:
            return

        nm = nmap.PortScanner()
        ports_str = ','.join(map(str, self.common_ports))
        scan_arguments = f"-sT -p {ports_str}"

        if deep_scan:
            # Service version detection (works without root)
            scan_arguments += " -sV --version-intensity 2"
            # SMB OS discovery and share enumeration (NSE scripts, no root needed)
            scan_arguments += " --script smb-os-discovery.nse"

        try:
            nm.scan(hosts=str(host), arguments=scan_arguments)
        except nmap.nmap.PortScannerError as e:
            print(_("Nmap error on host {host}: {e}").format(host=host, e=e))
            return

        if str(host) in nm.all_hosts():
            host_info = nm[str(host)]
            hostname = host_info.hostname() or None
            open_ports = []

            if 'tcp' in host_info:
                for port in host_info['tcp']:
                    if host_info['tcp'][port]['state'] == 'open':
                        open_ports.append(port)
            open_ports.sort()

            if host_info.state() == 'up':
                if not hostname:
                    hostname = netinfo.resolve_hostname(str(host))
                smb = 445 in open_ports or 139 in open_ports
                services = list(dict.fromkeys(
                    svc for port, svc in self.SERVICE_PORTS.items()
                    if port in open_ports
                ))

                device = {
                    "hostname": hostname or str(host),
                    "ip": str(host),
                    "ports": open_ports,
                    "ports_display": ", ".join(map(str, open_ports)) if open_ports else _("No common ports open"),
                    "smb": smb,
                    "services": services,
                    "os_display": "",
                }

                if deep_scan:
                    self._enrich_deep_scan(host_info, device, open_ports)

                device["deep_scanned"] = deep_scan

                with self.lock:
                    devices.append(device)
                    if generation is None or generation == self._scan_generation:
                        self.partial_results.append(device)

        with self.lock:
            if generation is None or generation == self._scan_generation:
                self.hosts_scanned += 1
                if progress_callback:
                    GLib.idle_add(progress_callback, self.hosts_scanned, self.total_hosts)

    def scan_network(self, ip_range, callback, error_callback, progress_callback=None, deep_scan=False):
        def do_scan():
            try:
                self.is_scanning = True
                self.partial_results = []
                self.hosts_scanned = 0
                self._scan_generation += 1
                gen = self._scan_generation

                hosts_to_scan = self.parse_ip_range_for_list(ip_range)
                self.total_hosts = len(hosts_to_scan)

                if progress_callback:
                    GLib.idle_add(progress_callback, 0, self.total_hosts)

                devices = []

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []
                    for host in hosts_to_scan:
                        if not self.is_scanning:
                            break
                        future = executor.submit(self.scan_single_ip, host, devices, progress_callback, deep_scan, gen)
                        futures.append(future)

                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            print(_("An error occurred in a thread: {e}").format(e=e))

                if self.is_scanning and gen == self._scan_generation:
                    self.is_scanning = False
                    devices_sorted = sorted(devices, key=lambda x: ipaddress.IPv4Address(x['ip']))
                    self._enrich_with_arp(devices_sorted)
                    GLib.idle_add(callback, devices_sorted)

            except Exception as e:
                self.is_scanning = False
                GLib.idle_add(error_callback, _("Scan failed: {e}").format(e=e))

        if not self.is_scanning:
            threading.Thread(target=do_scan, daemon=True).start()

    def stop_scan(self):
        self.is_scanning = False
        self._scan_generation += 1

    def get_partial_results(self):
        devices = sorted(self.partial_results, key=lambda x: ipaddress.IPv4Address(x['ip']))
        self._enrich_with_arp(devices)
        return devices

    @staticmethod
    def _enrich_deep_scan(host_info, device, open_ports):
        """Parse NSE script results and -sV service versions into OS and share info."""
        hostscript = host_info.get('hostscript', [])
        os_parts = []

        # 1. SMB OS discovery (most accurate for Windows hosts)
        for script in hostscript:
            if script.get('id') == 'smb-os-discovery':
                output = script.get('output', '')
                for line in output.split('\n'):
                    line = line.strip()
                    if line.startswith('OS:'):
                        os_parts.append(line[3:].strip())
                    elif line.startswith('|_'):
                        # Handle continuation lines
                        clean = line[2:].strip()
                        if clean.startswith('OS:'):
                            os_parts.append(clean[3:].strip())

        # 2. Service version info from -sV
        version_strings = []
        if 'tcp' in host_info:
            for port in open_ports:
                port_info = host_info['tcp'].get(port, {})
                product = port_info.get('product', '')
                version = port_info.get('version', '')
                if product:
                    parts = [product]
                    if version:
                        parts.append(version)
                    version_strings.append(' '.join(parts))

        if version_strings:
            # Deduplicate and limit to 3 services
            seen = list(dict.fromkeys(version_strings))
            os_parts.append(', '.join(seen[:3]))

        device["os_display"] = ' — '.join(os_parts) if os_parts else ''

    @staticmethod
    def _enrich_with_arp(devices):
        """Fill in MAC address from the kernel ARP table, best-effort."""
        arp_table = netinfo.read_arp_table()
        for device in devices:
            device["mac"] = arp_table.get(device["ip"], "")

    @staticmethod
    def _local_ip_via_udp_probe():
        """Ask the kernel which local address it would use to reach the internet.

        A UDP connect() only performs a routing decision - no packet is sent -
        so this works offline and needs no special permissions.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    @staticmethod
    def _default_gateway_from_proc_route():
        """Fallback: read the default gateway straight from the kernel route table."""
        with open('/proc/net/route') as f:
            lines = f.readlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            _iface, destination, gateway = parts[0], parts[1], parts[2]
            if destination == '00000000' and gateway != '00000000':
                packed = struct.pack('<L', int(gateway, 16))
                return socket.inet_ntoa(packed)
        return None

    @staticmethod
    def get_local_ip_range():
        """Detect the local /24 network range.

        Previously used socket.gethostbyname(gethostname()), which commonly
        resolves to 127.0.1.1 or the wrong interface depending on
        /etc/hosts - unreliable, especially inside the Flatpak sandbox. A UDP
        connect() only performs a kernel routing decision (no packet sent),
        so it reliably reveals the real outbound interface instead.
        """
        try:
            local_ip = NetworkScanner._local_ip_via_udp_probe()
            if local_ip:
                return str(ipaddress.IPv4Network(f"{local_ip}/24", strict=False))
        except OSError:
            pass

        try:
            gateway_ip = NetworkScanner._default_gateway_from_proc_route()
            if gateway_ip:
                return str(ipaddress.IPv4Network(f"{gateway_ip}/24", strict=False))
        except OSError:
            pass

        return "192.168.0.0/24"
