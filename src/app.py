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
        # Base path for Adw.Application automatic resources
        # (shortcuts-dialog.ui -> app.shortcuts + Ctrl+?).
        self.set_resource_base_path('/io/github/zingytomato/netpeek')
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
        self._create_app_actions()
        self._setup_accels()

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

    def _create_app_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.add_action(quit_action)

    def _setup_accels(self):
        # GNOME way: accelerators live on the application, actions on
        # app (global) or win (active window). Adw.Application provides
        # app.shortcuts (Ctrl+?) automatically from shortcuts-dialog.ui.
        self.set_accels_for_action("app.quit", ["<Primary>q"])
        self.set_accels_for_action("win.previous-scans", ["<Primary>h"])
        self.set_accels_for_action("win.go-back", ["<Alt>Left"])
        self.set_accels_for_action("win.start-scan", ["<Primary>Return"])
        self.set_accels_for_action("win.focus-ip", ["<Primary>l"])
        self.set_accels_for_action("win.find", ["<Primary>f"])
        self.set_accels_for_action("win.rescan", ["<Primary>r", "F5"])
        self.set_accels_for_action("win.stop-scan", ["<Primary>period"])
        self.set_accels_for_action("win.export", ["<Primary>e"])
        self.set_accels_for_action("win.toggle-view", ["<Primary>t"])
        self.set_accels_for_action("win.show-scan-info", ["<Primary>i"])

    def on_about_action(self, action, param):
        window = self.get_active_window()
        version = self.get_version()
        about = Adw.AboutDialog()
        about.set_application_name(_("NetPeek"))
        about.set_version(version)
        about.set_developer_name("ZingyTomato")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_comments(_("Discover devices on your local network."))
        about.set_website("https://github.com/zingytomato/netpeek")
        about.set_issue_url("https://github.com/zingytomato/netpeek/issues")
        about.add_link(_("Translate"), "https://hosted.weblate.org/engage/netpeek/")
        about.set_application_icon("io.github.zingytomato.netpeek")
        about.add_credit_section(_("Contributors"), ["ZingyTomato", "Gert-Dev", "Cameo007", "vmkspv", "oscfdezdz", "albanobattistella", "sjulien", "dawkagaming", "prescott66"])
        release_notes = """
        <ul>
          <li>Grouped all IP presets into a single button.</li>
          <li>Added date filters and custom date ranges to scan history.</li>
        </ul>
        """
        about.set_release_notes(release_notes)
        about.set_release_notes_version(version)
        about.present(window)

    def on_quit_action(self, action, param):
        self.quit()

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
