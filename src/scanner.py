import threading
import ipaddress
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from gi.repository import GLib

from gettext import gettext as _

class NetworkScanner:
    """Network scanning functionality"""

    def __init__(self):
        self.common_ports = [22, 80, 443, 3389, 53, 21, 23, 8080, 8443, 8006, 5000]
        self.is_scanning = False

    def validate_ip_range(self, ip_range):
        if not ip_range:
            return False, _("Please enter an IP range")

        try:
            if '/' in ip_range:
                ipaddress.ip_network(ip_range, strict=False)
            elif '-' in ip_range:
                base_ip, range_part = ip_range.rsplit('-', 1)
                base_parts = base_ip.split('.')

                if len(base_parts) == 4:
                    ipaddress.IPv4Address(base_ip)
                    int(range_part)
                elif len(base_parts) == 3:
                    ipaddress.IPv4Address(f"{base_ip}.1")
                    int(range_part)
                else:
                    raise ValueError(_("Invalid range format!"))
            else:
                ipaddress.IPv4Address(ip_range)

            return True, _("Valid IP range")

        except Exception as e:
            return False, _("Invalid IP range: ") + str(e)

    def auto_detect_network(self):
        try:
            result = subprocess.run(['ip', 'route', 'show', 'default'],
                                    capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'default via' in line:
                        parts = line.split()
                        gateway_ip = parts[2]
                        network = '.'.join(gateway_ip.split('.')[:-1]) + '.0/24'
                        return network, _("Auto-detected network: ") + network

            return "192.168.1.0/24", _("Using default network range")

        except Exception as e:
            print(_("Auto-detection failed: ") + str(e))
            return "192.168.1.0/24", _("Using default network range")

    def is_port_open(self, ip, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((ip, port)) == 0
        except:
            return False

    def scan_single_ip(self, ip_str, lock, devices):
        alive = False
        open_ports = []

        for port in self.common_ports:
            if self.is_port_open(ip_str, port):
                alive = True
                open_ports.append(port)

        if not alive:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    if s.connect_ex((ip_str, 80)) == 0:
                        alive = True
            except:
                pass

        if alive:
            hostname = ip_str
            try:
                hostname = socket.gethostbyaddr(ip_str)[0]
            except:
                pass

            device = {
                "hostname": hostname,
                "ip": ip_str,
                "ports": ", ".join(map(str, open_ports)) if open_ports else _("Host alive (no open ports detected)")
            }

            with lock:
                devices.append(device)

    def parse_ip_range(self, ip_range):
        hosts = []

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

            hosts = [ipaddress.IPv4Address(f"{base_network}.{i}")
                     for i in range(start_ip, end_ip + 1)]
        else:
            hosts = [ipaddress.IPv4Address(ip_range)]

        return hosts

    def scan_network(self, ip_range, callback, error_callback):
        def do_scan():
            try:
                self.is_scanning = True
                devices = []
                lock = threading.Lock()

                hosts = self.parse_ip_range(ip_range)

                with ThreadPoolExecutor(max_workers=20) as executor:
                    futures = []
                    for host in hosts:
                        if not self.is_scanning:
                            break
                        future = executor.submit(self.scan_single_ip, str(host), lock, devices)
                        futures.append(future)

                    for future in futures:
                        if not self.is_scanning:
                            break
                        future.result()

                self.is_scanning = False
                GLib.idle_add(callback, devices)

            except Exception as e:
                self.is_scanning = False
                GLib.idle_add(error_callback, _("Scan failed: ") + str(e))

        if not self.is_scanning:
            threading.Thread(target=do_scan, daemon=True).start()

    def stop_scan(self):
        self.is_scanning = False
