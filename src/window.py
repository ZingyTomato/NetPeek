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
        # Window-scoped actions. Accelerators are set centrally in
        # NetworkScannerApp._setup_accels() (the GNOME/GTK way).
        # app.quit / app.about live on the application (see app.py).
        win_actions = {
            "previous-scans": self.on_previous_scans_action,
            "find": self.on_find_action,
            "rescan": self.on_rescan_action,
            "start-scan": self.on_start_scan_action,
            "focus-ip": self.on_focus_ip_action,
            "stop-scan": self.on_stop_scan_action,
            "export": self.on_export_action,
            "toggle-view": self.on_toggle_view_action,
            "show-scan-info": self.on_show_scan_info_action,
            "go-back": self.on_go_back_action,
        }
        for name, handler in win_actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

    def on_find_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.results_page:
            self.results_page.focus_search()

    def on_rescan_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.results_page:
            self.results_page.on_rescan_clicked(None)

    def on_start_scan_action(self, action, param):
        visible = self.navigation_view.get_visible_page()
        if visible == self.home_page:
            self.home_page.on_scan_clicked(None)
        elif visible == self.results_page:
            # Ctrl+Enter on results behaves like rescan.
            self.results_page.on_rescan_clicked(None)

    def on_focus_ip_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.home_page:
            self.home_page.focus_ip_entry()

    def on_stop_scan_action(self, action, param):
        if self.navigation_view.get_visible_page() != self.results_page:
            return
        # Let the search entry consume Ctrl+. first for its emoji picker;
        # otherwise stop the scan.
        if self.results_page.search_entry.is_focus():
            return
        self.results_page.stop_if_scanning()

    def on_export_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.results_page:
            self.results_page.export_results()

    def on_toggle_view_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.results_page:
            self.results_page.toggle_view()

    def on_show_scan_info_action(self, action, param):
        if self.navigation_view.get_visible_page() == self.results_page:
            self.results_page.show_scan_info()

    def on_go_back_action(self, action, param):
        if self.navigation_view.get_visible_page() != self.home_page:
            self.navigation_view.pop()

    def on_previous_scans_action(self, action, param):
        """Show the previous scans dialog"""
        dialog = HistoryDialog(self.on_history_scan_selected, settings=self.settings)
        dialog.present(self)

    def on_history_scan_selected(self, scan):
        """Load a scan chosen from history into the results page"""
        if self.navigation_view.get_visible_page() != self.results_page:
            self.navigation_view.push(self.results_page)
        self.results_page.load_from_history(scan)
        self._came_from_history = True

    def _on_page_popped(self, navigation_view, page):
        """Reopen the history dialog when navigating back from a scan loaded from history."""
        if self._came_from_history and page == self.results_page:
            self._came_from_history = False
            dialog = HistoryDialog(self.on_history_scan_selected, settings=self.settings)
            dialog.present(self)

    def setup_pages(self):
        self.home_page = HomePage(
            window=self,
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
