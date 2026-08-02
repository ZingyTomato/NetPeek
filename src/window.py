# window.py
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
from gi.repository import Gtk, Adw, Gio

from .scanner import NetworkScanner
from .pages import HomePage, ResultsPage, HistoryDialog

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/main_window.ui')
class NetworkScannerWindow(Adw.ApplicationWindow):
    """Main application window"""
    __gtype_name__ = 'NetworkScannerWindow'

    toast_overlay = Gtk.Template.Child()
    navigation_view = Gtk.Template.Child()

    def __init__(self, settings, **kwargs):
        super().__init__(**kwargs)

        self.settings = settings
        self.scanner = NetworkScanner()
        self._came_from_history = False
        self.setup_pages()
        self.create_actions()

    def create_actions(self):
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.get_application().add_action(about_action)

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.get_application().add_action(quit_action)

        previous_scans_action = Gio.SimpleAction.new("previous-scans", None)
        previous_scans_action.connect("activate", self.on_previous_scans_action)
        self.add_action(previous_scans_action)

    def on_about_action(self, action, param):
        version = self.get_application().get_version()
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
          <li>Device cards now cap System Information and Services at one line, with expand/collapse buttons to reveal the full text.</li>
          <li>Moved the thread count picker into the main menu.</li>
          <li>Added better indication throughout the UI that a deep scan is taking place.</li>
          <li>Added a Translate link to the About dialog.</li>
        </ul>
        """
        about.set_release_notes(release_notes)
        about.set_release_notes_version(version)
        about.present(self)

    def on_quit_action(self, action, param):
        self.get_application().quit()

    def on_previous_scans_action(self, action, param):
        """Show the previous scans dialog"""
        dialog = HistoryDialog(self.on_history_scan_selected)
        dialog.present(self)

    def on_history_scan_selected(self, scan):
        """Load a scan chosen from history into the results page"""
        if self.navigation_view.get_visible_page() != self.results_page:
            self.navigation_view.push(self.results_page)
        self.results_page.load_from_history(scan.get('ip_range', ''), scan.get('devices', []), scan.get('deep_scan', False))
        self._came_from_history = True

    def _on_page_popped(self, navigation_view, page):
        """Re-open history dialog when navigating back from a history-loaded scan."""
        if self._came_from_history and page == self.results_page:
            self._came_from_history = False
            dialog = HistoryDialog(self.on_history_scan_selected)
            dialog.present(self)

    def setup_pages(self):
        self.home_page = HomePage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner,
            settings=self.settings,
        )

        self.results_page = ResultsPage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner,
            settings=self.settings,
        )

        self.home_page.connect_results_page(self.results_page)
        self.results_page.connect_home_page(self.home_page)

        self.navigation_view.connect("popped", self._on_page_popped)

        self.navigation_view.add(self.home_page)
