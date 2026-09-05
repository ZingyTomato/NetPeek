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

class DeviceMobileRow(ToastMixin, Adw.ExpanderRow):
    """Device row for the list view; recycled by the factory."""
    __gtype_name__ = 'DeviceMobileRow'

    def __init__(self, toast_overlay=None):
        super().__init__()
        self.toast_overlay = toast_overlay
        self._device = None
        self._name_binding = None
        self._notify_handler = None
        self._copy_handler = None
        self._name_activate_handler = None
        self._name_apply_handler = None
        self._focus_controller = None
        try:
            self.clipboard = Gdk.Display.get_default().get_clipboard()
        except Exception:
            self.clipboard = None

        self.set_title_lines(1)
        self.set_subtitle_lines(1)
        self.add_css_class("mobile-device-row")

        self._status_icon = Gtk.Image()
        self._status_icon.set_valign(Gtk.Align.CENTER)
        self.add_prefix(self._status_icon)

        self._new_badge = Gtk.Label(label=_("New"))
        self._new_badge.set_valign(Gtk.Align.CENTER)
        self._new_badge.add_css_class("accent")
        self._new_badge.add_css_class("caption-heading")
        self.add_suffix(self._new_badge)

        self._copy_button = Gtk.Button()
        self._copy_button.set_icon_name("edit-copy-symbolic")
        self._copy_button.set_valign(Gtk.Align.CENTER)
        self._copy_button.set_tooltip_text(_("Click to copy IP"))
        self.add_suffix(self._copy_button)

        self._name_row = Adw.EntryRow(title=_("Name"))
        self._name_apply_button = Gtk.Button()
        self._name_apply_button.set_icon_name("object-select-symbolic")
        self._name_apply_button.set_valign(Gtk.Align.CENTER)
        self._name_apply_button.add_css_class("flat")
        self._name_apply_button.set_tooltip_text(_("Apply name"))
        self._name_row.add_suffix(self._name_apply_button)
        self.add_row(self._name_row)

        self._hostname_row = Adw.ActionRow(title=_("Hostname"))
        self._hostname_row.set_subtitle_selectable(True)
        hostname_icon = Gtk.Image.new_from_icon_name("computer-symbolic")
        self._hostname_row.add_prefix(hostname_icon)
        self.add_row(self._hostname_row)

        self._ports_row = Adw.ActionRow(title=_("Ports Open"))
        self._ports_row.set_subtitle_selectable(True)
        ports_icon = Gtk.Image.new_from_icon_name(
            "network-transmit-receive-symbolic")
        self._ports_row.add_prefix(ports_icon)
        self.add_row(self._ports_row)

        self._services_row = Adw.ActionRow(title=_("Services"))
        self._services_row.set_subtitle_selectable(True)
        services_icon = Gtk.Image.new_from_icon_name("folder-remote-symbolic")
        self._services_row.add_prefix(services_icon)
        self.add_row(self._services_row)

        self._os_row = Adw.ActionRow(title=_("System Information"))
        self._os_row.set_subtitle_selectable(True)
        os_icon = Gtk.Image.new_from_icon_name("computer-symbolic")
        self._os_row.add_prefix(os_icon)
        self.add_row(self._os_row)

        self._focus_controller = Gtk.EventControllerFocus()
        self._focus_controller.connect(
            "enter", lambda c: self._name_apply_button.set_visible(True))
        self._focus_controller.connect(
            "leave", lambda c: self._name_apply_button.set_visible(False))
        self._name_row.add_controller(self._focus_controller)
        self._name_apply_button.set_visible(False)

    def bind_device(self, device):
        self.unbind_device()
        self._device = device
        # Reset recycled state.
        self.set_expanded(False)

        self._name_binding = device.bind_property(
            "custom-name", self._name_row, "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        self._notify_handler = device.connect(
            "notify::custom-name", lambda *_: self._refresh_header())
        self._copy_handler = self._copy_button.connect(
            "clicked", lambda _b: self._on_copy_clicked())
        self._name_activate_handler = self._name_row.connect(
            "entry-activated", lambda _r: self._on_name_apply())
        self._name_apply_handler = self._name_apply_button.connect(
            "clicked", lambda _b: self._on_name_apply())

        self._refresh_header()
        self._hostname_row.set_subtitle(
            device.hostname if device.hostname != device.ip else _("Unknown"))
        self._ports_row.set_subtitle(device.ports_display)
        self._services_row.set_subtitle(device.services_display)
        self._services_row.set_visible(bool(device.services_display))
        self._os_row.set_subtitle(device.os_display)
        self._os_row.set_visible(device.deep_scanned)

    def unbind_device(self):
        if self._device is not None and self._notify_handler is not None:
            try:
                self._device.disconnect(self._notify_handler)
            except Exception:
                pass
        self._notify_handler = None
        if self._name_binding is not None:
            try:
                self._name_binding.unbind()
            except Exception:
                pass
        self._name_binding = None
        if self._copy_handler is not None:
            try:
                self._copy_button.disconnect(self._copy_handler)
            except Exception:
                pass
        self._copy_handler = None
        if self._name_activate_handler is not None:
            try:
                self._name_row.disconnect(self._name_activate_handler)
            except Exception:
                pass
        self._name_activate_handler = None
        if self._name_apply_handler is not None:
            try:
                self._name_apply_button.disconnect(self._name_apply_handler)
            except Exception:
                pass
        self._name_apply_handler = None
        self._device = None

    def _refresh_header(self):
        device = self._device
        if device is None:
            return
        hostname_known = device.hostname and device.hostname != device.ip
        title = device.ip
        if device.custom_name:
            subtitle = device.custom_name
            if hostname_known and device.hostname != device.custom_name:
                subtitle += " · " + device.hostname
        elif hostname_known:
            subtitle = device.hostname
        else:
            subtitle = device.ports_display or _("Unknown device")
        self.set_title(title)
        self.set_subtitle(subtitle)

        if not device.known:
            self._status_icon.set_from_icon_name("starred-symbolic")
            self._status_icon.set_tooltip_text(_("New device"))
            self._status_icon.add_css_class("accent")
            self._new_badge.set_visible(True)
        else:
            self._status_icon.set_from_icon_name("network-wired-symbolic")
            self._status_icon.set_tooltip_text(_("Known device"))
            self._status_icon.remove_css_class("accent")
            self._new_badge.set_visible(False)

    def _on_copy_clicked(self):
        if self._device is None or self.clipboard is None:
            return
        ip_text = self._device.ip
        self.clipboard.set(ip_text)
        if self.toast_overlay is not None:
            self.show_toast(_("Copied {ip} to the clipboard").format(ip=ip_text))

    def _on_name_apply(self):
        if self._device is None:
            return
        storage.set_custom_name(
            self._device.registry_key, self._device.custom_name)
        self._refresh_header()
        root = self.get_root()
        if root:
            root.set_focus(None)
        try:
            self._name_row.set_position(-1)
        except Exception:
            pass


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
