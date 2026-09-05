# models.py
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

import ipaddress

from gi.repository import GObject

# Distinctive ports mapped to service names.
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

SERVICE_LABELS = {
    "smb": _("SMB shares"),
    "cockpit": _("Cockpit"),
    "mysql": _("MySQL"),
    "postgresql": _("PostgreSQL"),
    "redis": _("Redis"),
    "homeassistant": _("Home Assistant"),
    "plex": _("Plex"),
    "cups": _("CUPS"),
    "mongodb": _("MongoDB"),
    "proxmox": _("Proxmox"),
    "synology": _("Synology DSM"),
}

# Scanned even when they don't map to a known service.
BASE_PORTS = [22, 80, 443, 3389, 53, 21, 23, 8080, 8443, 5000, 3000, 9000]


def dedup(seq):
    return list(dict.fromkeys(seq))


class Device(GObject.Object):
    """A discovered network device, bindable to card and list views."""

    __gtype_name__ = "NetpeekDevice"

    ip = GObject.Property(type=str, default="")
    hostname = GObject.Property(type=str, default="")
    custom_name = GObject.Property(type=str, default="")
    ports_display = GObject.Property(type=str, default="")
    services_display = GObject.Property(type=str, default="")
    known = GObject.Property(type=bool, default=False)
    known_int = GObject.Property(type=int, default=0)
    ip_sort_key = GObject.Property(type=GObject.TYPE_UINT64, default=0)
    os_display = GObject.Property(type=str, default="")
    deep_scanned = GObject.Property(type=bool, default=False)

    def __init__(self, data):
        super().__init__()
        self.ip = data.get("ip", "")
        self.hostname = data.get("hostname") or self.ip
        self.custom_name = data.get("custom_name", "") or ""
        self.ports_display = data.get("ports_display", "")
        self.services = data.get("services") or []
        self.services_display = ", ".join(SERVICE_LABELS.get(s, s) for s in self.services)
        self.known = bool(data.get("known", False))
        self.known_int = 1 if self.known else 0
        self.ip_sort_key = self._ip_to_int(self.ip)
        self.os_display = data.get("os_display", "") or ""
        self.deep_scanned = data.get("deep_scanned", False)

    @staticmethod
    def _ip_to_int(ip):
        try:
            return int(ipaddress.IPv4Address(ip))
        except ValueError:
            return 0

    @property
    def display_name(self):
        if self.custom_name:
            return self.custom_name
        if self.hostname and self.hostname != self.ip:
            return self.hostname
        return self.ip

    @property
    def hostname_or_unknown(self):
        if self.hostname and self.hostname != self.ip:
            return self.hostname
        return _("Unknown")

    def header_subtitle(self):
        if self.custom_name:
            if self.hostname and self.hostname != self.ip and self.hostname != self.custom_name:
                return f"{self.custom_name} · {self.hostname}"
            return self.custom_name
        if self.hostname and self.hostname != self.ip:
            return self.hostname
        return self.ports_display or _("Unknown device")

    @property
    def registry_key(self):
        return self.ip
