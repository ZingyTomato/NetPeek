# widgets.py
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

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/device_card.ui')
class DeviceCard(Adw.Bin):
    """Custom widget for displaying device information in a card format"""
    __gtype_name__ = 'DeviceCard'

    ip_row = Gtk.Template.Child()
    hostname_row = Gtk.Template.Child()
    ports_row = Gtk.Template.Child()

    def __init__(self, device_info=None):
        super().__init__()

        if device_info:
            self.set_device_info(device_info)

    def set_device_info(self, device_info):
        """Set the device information"""
        ip_address = device_info.get('ip', _("Unknown IP"))
        self.ip_row.set_title(ip_address)

        hostname = device_info.get('hostname', _("Unknown"))
        if hostname == ip_address:
            hostname = _("Unknown")
        self.hostname_row.set_subtitle(hostname)

        ports = device_info.get('ports', _("No Ports Open"))
        self.ports_row.set_subtitle(ports)

class PresetButton(Gtk.Button):
    """Custom preset button for IP ranges"""

    def __init__(self, preset_range, tooltip_text, callback=None):
        super().__init__()

        ip_address = preset_range.split("/")[0].split(".")
        prefix_length = int(preset_range.split("/")[1]) // 8
        ip_address[prefix_length:] = ["x" for _ in range(4 - prefix_length)]

        self.set_label(".".join(ip_address))
        self.set_tooltip_text(_(tooltip_text))
        self.add_css_class("pill")

        self.preset_range = preset_range

        if callback:
            self.connect('clicked', callback, preset_range)

class StatusIndicator(Gtk.Box):
    """Custom status indicator widget"""

    def __init__(self, status="online"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_spacing(6)
        self.set_valign(Gtk.Align.CENTER)

        self.indicator = Gtk.Image()
        self.set_status(status)

        self.append(self.indicator)

    def set_status(self, status):
        """Set the status indicator"""
        if status == "online":
            self.indicator.set_from_icon_name("network-wireless-signal-excellent-symbolic")
            self.indicator.add_css_class("success")
        elif status == "offline":
            self.indicator.set_from_icon_name("network-wireless-offline-symbolic")
            self.indicator.add_css_class("error")
        elif status == "scanning":
            self.indicator.set_from_icon_name("network-wireless-acquiring-symbolic")
            self.indicator.add_css_class("warning")
