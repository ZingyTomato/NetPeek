# window.py
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
from gi.repository import Gtk, Adw, Gio

from .scanner import NetworkScanner
from .pages import HomePage, ResultsPage

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/main_window.ui')
class NetworkScannerWindow(Adw.ApplicationWindow):
    """Main application window"""
    __gtype_name__ = 'NetworkScannerWindow'

    toast_overlay = Gtk.Template.Child()
    navigation_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.scanner = NetworkScanner()
        self.setup_pages()
        self.create_actions()

    def create_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.get_application().add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.get_application().add_action(quit_action)

    def on_about_action(self, action, param):
        about = Adw.AboutDialog()
        about.set_application_name(_("NetPeek"))
        about.set_version("0.2.2")
        about.set_developer_name("ZingyTomato")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_comments(_("Discover devices on your local network."))
        about.set_website("https://github.com/zingytomato/netpeek")
        about.set_issue_url("https://github.com/zingytomato/netpeek/issues")
        about.set_application_icon("io.github.zingytomato.netpeek")
        about.add_credit_section(_("Contributors"), ["ZingyTomato", "Gert-Dev", "Cameo007", "vmkspv"])
        about.present(self)

    def on_quit_action(self, action, param):
        self.get_application().quit()

    def setup_pages(self):
        self.home_page = HomePage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner
        )

        self.results_page = ResultsPage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner
        )

        self.home_page.connect_results_page(self.results_page)
        self.results_page.connect_home_page(self.home_page)

        self.navigation_view.add(self.home_page)

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
