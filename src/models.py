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

from . import storage


class Device(GObject.Object):
    """A discovered network device, bindable to both card and list views."""

    __gtype_name__ = "NetpeekDevice"

    ip = GObject.Property(type=str, default="")
    hostname = GObject.Property(type=str, default="")
    custom_name = GObject.Property(type=str, default="")
    mac = GObject.Property(type=str, default="")
    ports_display = GObject.Property(type=str, default="")
    smb = GObject.Property(type=bool, default=False)
    known = GObject.Property(type=bool, default=False)
    known_int = GObject.Property(type=int, default=0)
    ip_sort_key = GObject.Property(type=GObject.TYPE_UINT64, default=0)

    def __init__(self, data):
        super().__init__()
        self.ip = data.get("ip", "")
        self.hostname = data.get("hostname") or self.ip
        self.custom_name = data.get("custom_name", "") or ""
        self.mac = data.get("mac", "") or ""
        self.ports = data.get("ports", [])
        self.ports_display = data.get("ports_display", "")
        self.smb = bool(data.get("smb", False))
        self.known = bool(data.get("known", False))
        self.known_int = 1 if self.known else 0
        self.ip_sort_key = self._ip_to_int(self.ip)

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
        return storage.device_key(self.mac, self.ip)

    def to_dict(self):
        return {
            "ip": self.ip,
            "hostname": self.hostname,
            "custom_name": self.custom_name,
            "mac": self.mac,
            "ports": self.ports,
            "ports_display": self.ports_display,
            "smb": self.smb,
            "known": self.known,
        }
