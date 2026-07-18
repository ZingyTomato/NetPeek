# widgets.py
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

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GObject

from . import storage

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/device_card.ui')
class DeviceCard(Adw.Bin):
    """Custom widget for displaying device information in a card format"""
    __gtype_name__ = 'DeviceCard'

    name_row = Gtk.Template.Child()
    new_badge = Gtk.Template.Child()
    ip_row = Gtk.Template.Child()
    hostname_row = Gtk.Template.Child()
    ports_row = Gtk.Template.Child()
    smb_row = Gtk.Template.Child()

    def __init__(self, device, toast_overlay, on_rename=None):
        super().__init__()
        self.device = device
        self.toast_overlay = toast_overlay
        self._on_rename = on_rename
        self.clipboard = Gdk.Display.get_default().get_clipboard()

        # Bidirectional binding keeps this card's name entry and the list
        # view's custom name column in sync live, without either widget
        # having to know about the other.
        device.bind_property(
            "custom-name", self.name_row, "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        self.refresh()

    def refresh(self):
        """Populate the card from the bound Device model"""
        device = self.device

        self.new_badge.set_visible(not device.known)

        self.ip_row.set_title(device.ip)
        self.hostname_row.set_subtitle(device.hostname if device.hostname != device.ip else _("Unknown"))
        self.ports_row.set_subtitle(device.ports_display)
        self.smb_row.set_visible(device.smb)

    @Gtk.Template.Callback()
    def on_ip_clicked(self, button):
        """Copy the IP address when the copy button is clicked"""
        ip_text = self.ip_row.get_title()
        self.clipboard.set(ip_text)
        self.show_toast(_("Copied {ip} to the clipboard").format(ip=ip_text))

    @Gtk.Template.Callback()
    def on_name_apply(self, entry_row):
        """Persist a custom name when the entry row's apply button is used"""
        # entry_row.text is already synced onto self.device.custom_name via
        # the bind_property() set up in __init__.
        storage.set_custom_name(self.device.registry_key, self.device.custom_name)
        if self._on_rename:
            self._on_rename(self.device)

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)

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
