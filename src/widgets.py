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
from gi.repository import Gtk, Adw, Gdk, GObject, GLib

from . import storage


class ToastMixin:
    """Shared show_toast helper for widgets that have a toast_overlay."""

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/device_card.ui')
class DeviceCard(ToastMixin, Adw.Bin):
    """Custom widget for displaying device information in a card format"""
    __gtype_name__ = 'DeviceCard'

    name_row = Gtk.Template.Child()
    name_apply_button = Gtk.Template.Child()
    new_badge = Gtk.Template.Child()
    ip_row = Gtk.Template.Child()
    hostname_row = Gtk.Template.Child()
    ports_row = Gtk.Template.Child()
    services_row = Gtk.Template.Child()
    services_expand_button = Gtk.Template.Child()
    os_row = Gtk.Template.Child()
    os_expand_button = Gtk.Template.Child()

    def __init__(self, device, toast_overlay):
        super().__init__()
        self.device = device
        self.toast_overlay = toast_overlay
        self.clipboard = Gdk.Display.get_default().get_clipboard()
        self._os_checked = False
        self._services_checked = False
        self.os_row.connect("map", self._on_row_map)
        self.services_row.connect("map", self._on_row_map)

        # Bidirectional binding keeps this card's name entry and the list
        # view's custom name column in sync live, without either widget
        # having to know about the other.
        device.bind_property(
            "custom-name", self.name_row, "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("enter", lambda c: self.name_apply_button.set_visible(True))
        focus_controller.connect("leave", lambda c: self.name_apply_button.set_visible(False))
        self.name_row.add_controller(focus_controller)

        self.refresh()

    def refresh(self):
        """Populate the card from the bound Device model"""
        device = self.device

        self.new_badge.set_visible(not device.known)

        self.ip_row.set_title(device.ip)
        self.hostname_row.set_subtitle(device.hostname if device.hostname != device.ip else _("Unknown"))
        self.ports_row.set_subtitle(device.ports_display)
        self.services_row.set_subtitle(device.services_display)
        self.services_row.set_tooltip_text(device.services_display if device.services_display else None)
        self.services_row.set_subtitle_lines(1)
        self.services_expand_button.set_visible(False)
        self.services_expand_button.set_active(False)
        self._services_checked = False

        self.os_row.set_subtitle(device.os_display)
        self.os_row.set_tooltip_text(device.os_display if device.os_display else None)
        self.os_row.set_visible(device.deep_scanned)
        # The expand button only makes sense when the info actually wraps to
        # more than one line; ellipsization is checked once the row is laid
        # out (see _on_os_row_map).
        self.os_expand_button.set_visible(False)
        self.os_expand_button.set_active(False)
        self.os_row.set_subtitle_lines(1)
        self._os_checked = False

    def _find_subtitle_label(self, row):
        """Find the GtkLabel used for the row's subtitle"""
        child = row.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Label) and "subtitle" in child.get_css_classes():
                return child
            found = self._find_subtitle_label(child)
            if found:
                return found
            child = child.get_next_sibling()
        return None

    def _row_state(self, row):
        """Return (expand_button, checked_flag) for a given subtitle row"""
        if row is self.os_row:
            return self.os_expand_button, "_os_checked"
        return self.services_expand_button, "_services_checked"

    def _on_row_map(self, row):
        """Check ellipsization once the row is mapped and laid out"""
        _button, checked_flag = self._row_state(row)
        if not getattr(self, checked_flag):
            GLib.idle_add(self._check_ellipsized, row)

    def _check_ellipsized(self, row):
        """Show the expand button only when the subtitle is ellipsized"""
        if not row.get_mapped():
            return GLib.SOURCE_CONTINUE
        label = self._find_subtitle_label(row)
        layout = label.get_layout() if label else None
        if layout is None or label.get_width() <= 1:
            return GLib.SOURCE_CONTINUE
        button, checked_flag = self._row_state(row)
        setattr(self, checked_flag, True)
        button.set_visible(layout.is_ellipsized())
        return GLib.SOURCE_REMOVE

    def _set_expanded(self, row, button, expanded, full_tooltip):
        """Expand/collapse a row's subtitle"""
        row.set_subtitle_lines(0 if expanded else 1)
        button.set_icon_name("pan-up-symbolic" if expanded else "pan-down-symbolic")
        button.set_tooltip_text(_("Show less") if expanded else full_tooltip)

    @Gtk.Template.Callback()
    def on_expand_toggled(self, button):
        """Toggle expansion for the row the button belongs to"""
        expanded = button.get_active()
        if button is self.os_expand_button:
            self._set_expanded(self.os_row, button, expanded,
                               _("Show full system information"))
        elif button is self.services_expand_button:
            self._set_expanded(self.services_row, button, expanded,
                               _("Show full service list"))

    @Gtk.Template.Callback()
    def on_ip_clicked(self, button):
        ip_text = self.ip_row.get_title()
        self.clipboard.set(ip_text)
        self.show_toast(_("Copied {ip} to the clipboard").format(ip=ip_text))

    @Gtk.Template.Callback()
    def on_name_apply(self, _widget):
        """Persist a custom name when the apply button is clicked or Enter is pressed"""
        # The name entry's text is already synced onto self.device.custom_name
        # via the bind_property() set up in __init__.
        storage.set_custom_name(self.device.registry_key, self.device.custom_name)
        root = self.get_root()
        if root:
            root.set_focus(None)
        self.name_row.set_position(-1)

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/theme_selector.ui')
class ThemeSelector(Gtk.Box):
    """Light/dark/system swatch selector shown in the primary menu."""
    __gtype_name__ = 'ThemeSelector'

    auto_button = Gtk.Template.Child()
    light_button = Gtk.Template.Child()
    dark_button = Gtk.Template.Child()

    def __init__(self, settings):
        super().__init__()
        self.schemes = {
            self.auto_button: "default",
            self.light_button: "light",
            self.dark_button: "dark",
        }

        current = settings.get_string("color-scheme")
        for button, scheme in self.schemes.items():
            button.set_active(scheme == current)

        # Connected after the initial state is set so restoring the saved
        # scheme doesn't reactivate the action before we're in a window.
        for button in self.schemes:
            button.connect("toggled", self.on_option_selected)

    def on_option_selected(self, button):
        if button.get_active():
            self.activate_action(
                "app.color-scheme", GLib.Variant("s", self.schemes[button]))


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
