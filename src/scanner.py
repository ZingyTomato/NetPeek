# scanner.py
#
# Copyright 2025 ZingyTomato
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
import nmap
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from gi.repository import GLib

class NetworkScanner:
    """Network scanning functionality with caching and custom names"""

    def __init__(self):
        self.common_ports = [22, 80, 443, 3389, 53, 21, 23, 8080, 8443, 8006, 5000]
        self.is_scanning = False
        self.hosts_scanned = 0
        self.total_hosts = 0
        self.partial_results = []
        self.lock = threading.Lock()

        self.max_workers = 100

        self.cache_dir = Path.home() / ".cache" / "netpeek"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "device_cache.json"
        self.custom_names_file = self.cache_dir / "custom_names.json"

        self.device_cache = {}
        self.custom_names = {}

        self.load_cache()

    def set_max_workers(self, count):
        """Set the maximum number of worker threads"""
        if 1 <= count <= 500:
            self.max_workers = count
        else:
            print(_("Thread count must be between 1 and 500"))

    def load_cache(self):
        """Load cached devices and custom names from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.device_cache = json.load(f)
        except Exception as e:
            print(_("Failed to load device cache: {e}").format(e=e))
            self.device_cache = {}

        try:
            if self.custom_names_file.exists():
                with open(self.custom_names_file, 'r') as f:
                    self.custom_names = json.load(f)
        except Exception as e:
            print(_("Failed to load custom names: {e}").format(e=e))
            self.custom_names = {}

    def save_cache(self):
        """Save device cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.device_cache, f, indent=2)
        except Exception as e:
            print(_("Failed to save device cache: {e}").format(e=e))

    def save_custom_names(self):
        """Save custom names to disk"""
        try:
            with open(self.custom_names_file, 'w') as f:
                json.dump(self.custom_names, f, indent=2)
        except Exception as e:
            print(_("Failed to save custom names: {e}").format(e=e))

    def update_cache(self, devices):
        """Update cache with newly scanned devices"""
        import time
        current_time = time.time()

        for device in devices:
            ip = device['ip']
            self.device_cache[ip] = {
                'hostname': device['hostname'],
                'ports': device['ports'],
                'last_seen': current_time
            }

        self.save_cache()

    def is_new_device(self, ip):
        """Check if a device is new (not in cache)"""
        return ip not in self.device_cache

    def get_custom_name(self, ip):
        """Get custom name for an IP address"""
        return self.custom_names.get(ip)

    def set_custom_name(self, ip, custom_name):
        """Set custom name for an IP address"""
        if custom_name and custom_name.strip():
            self.custom_names[ip] = custom_name.strip()
        elif ip in self.custom_names:
            del self.custom_names[ip]

        self.save_custom_names()

    def get_cached_devices(self):
        """Get all cached devices"""
        return [
            {
                'ip': ip,
                'hostname': data['hostname'],
                'ports': data['ports'],
                'last_seen': data.get('last_seen', 0)
            }
            for ip, data in self.device_cache.items()
        ]

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

    def scan_single_ip(self, host, devices, progress_callback=None):
        if not self.is_scanning:
            return

        nm = nmap.PortScanner()
        scan_arguments = f"-sT -p {','.join(map(str, self.common_ports))}"

        try:
            nm.scan(hosts=str(host), arguments=scan_arguments)
        except nmap.nmap.PortScannerError as e:
            print(_("Nmap error on host {host}: {e}").format(host=host, e=e))
            return

        if str(host) in nm.all_hosts():
            host_info = nm[str(host)]
            hostname = host_info.hostname() if host_info.hostname() else str(host)
            open_ports = []

            if 'tcp' in host_info:
                for port in host_info['tcp']:
                    if host_info['tcp'][port]['state'] == 'open':
                        open_ports.append(port)

            if host_info.state() == 'up':
                device = {
                    "hostname": hostname,
                    "ip": str(host),
                    "ports": _("Host alive (no common ports detected)") if not open_ports else ", ".join(map(str, open_ports))
                }
                with self.lock:
                    devices.append(device)
                    self.partial_results.append(device)

        with self.lock:
            self.hosts_scanned += 1
            if progress_callback:
                GLib.idle_add(progress_callback, self.hosts_scanned, self.total_hosts)

    def scan_network(self, ip_range, callback, error_callback, progress_callback=None):
        def do_scan():
            try:
                self.is_scanning = True
                self.partial_results = []
                self.hosts_scanned = 0

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
                        future = executor.submit(self.scan_single_ip, host, devices, progress_callback)
                        futures.append(future)

                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            print(_("An error occurred in a thread: {e}").format(e=e))

                if self.is_scanning:
                    self.is_scanning = False
                    devices_sorted = sorted(devices, key=lambda x: ipaddress.IPv4Address(x['ip']))
                    GLib.idle_add(callback, devices_sorted)

            except Exception as e:
                self.is_scanning = False
                GLib.idle_add(error_callback, _("Scan failed: {e}").format(e=e))

        if not self.is_scanning:
            threading.Thread(target=do_scan, daemon=True).start()

    def stop_scan(self):
        self.is_scanning = False

    def get_partial_results(self):
        return sorted(self.partial_results, key=lambda x: ipaddress.IPv4Address(x['ip']))

    def get_local_ip_range():
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        except Exception:
            network = ipaddress.IPv4Network("192.168.0.1/24", strict=False)
        return str(network)
