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


class Device(GObject.Object):
    """A discovered network device, bindable to both card and list views."""

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
        service_labels = {
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
        self.services_display = ", ".join(service_labels.get(s, s) for s in self.services)
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
    def registry_key(self):
        return self.ip
