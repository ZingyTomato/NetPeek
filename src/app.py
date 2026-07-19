# app.py
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
from gi.repository import Gtk, Adw, Gdk, Gio, GLib

from .window import NetworkScannerWindow

COLOR_SCHEMES = {
    "light": Adw.ColorScheme.FORCE_LIGHT,
    "dark": Adw.ColorScheme.FORCE_DARK,
    "default": Adw.ColorScheme.DEFAULT,
}

class NetworkScannerApp(Adw.Application):
    """Main application class for NetPeek"""

    def __init__(self):
        super().__init__(application_id='io.github.zingytomato.netpeek')
        self.settings = Gio.Settings.new('io.github.zingytomato.netpeek')

        self._create_color_scheme_action()
        self._apply_color_scheme()

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Make the bundled app icons resolvable without an installed icon
        # cache, so they also show up in development runs (e.g. Builder).
        Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_resource_path(
            '/io/github/zingytomato/netpeek/icons')
        self._load_css()

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_resource('/io/github/zingytomato/netpeek/gtk/style.css')
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _create_color_scheme_action(self):
        action = Gio.SimpleAction.new_stateful(
            "color-scheme",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string(self.settings.get_string("color-scheme")),
        )
        action.connect("activate", self.on_color_scheme_change)
        self.add_action(action)

    def on_color_scheme_change(self, action, value):
        action.set_state(value)
        self.settings.set_string("color-scheme", value.get_string())
        self._apply_color_scheme()

    def _apply_color_scheme(self):
        scheme = self.settings.get_string("color-scheme")
        Adw.StyleManager.get_default().set_color_scheme(
            COLOR_SCHEMES.get(scheme, Adw.ColorScheme.DEFAULT))

    def do_activate(self):
        """Called when the application is activated"""
        self.window = NetworkScannerWindow(application=self, settings=self.settings)
        self.window.present()
