# pages.py
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
import time

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from .widgets import DeviceCard, PresetButton

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/home_page.ui')
class HomePage(Adw.NavigationPage):
    """Home page with IP input functionality"""
    __gtype_name__ = 'HomePage'

    ip_entry_row = Gtk.Template.Child()
    scan_button = Gtk.Template.Child()
    preset_box = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.results_page = None

        self.setup_presets()

    def connect_results_page(self, results_page):
        self.results_page = results_page

    def setup_presets(self):
        """Setup preset IP range buttons"""
        presets = [
            ("192.168.1.0/24", _("Home Network (192.168.1.x)")),
            ("192.168.0.0/24", _("Home Network (192.168.0.x)")),
            ("10.0.0.0/24", _("Corporate (10.0.0.x)")),
            ("172.16.0.0/24", _("Private (172.16.0.x)"))
        ]

        for preset_range, tooltip in presets:
            preset_button = PresetButton(preset_range, tooltip, self.on_preset_clicked)
            self.preset_box.append(preset_button)

    @Gtk.Template.Callback()
    def on_scan_clicked(self, button):
        """Start scan when 'Scan My Network' is clicked"""
        if not self.validate_ip_range():
            return
        ip_range = self.ip_entry_row.get_text().strip()
        if self.results_page:
            self.navigation_view.push(self.results_page)
            self.results_page.start_scan(ip_range)

    @Gtk.Template.Callback()
    def on_ip_range_apply(self, entry_row):
        """If the check mark is clicked after entering an IP"""
        if self.validate_ip_range():
            self.show_toast(_("Valid IP range!"), 2)

    def on_preset_clicked(self, button, preset_range):
        """If one of the IP presets were clicked"""
        self.ip_entry_row.set_text(preset_range)
        self.show_toast(_("Set IP range to: ") + preset_range, 2)

    def validate_ip_range(self):
        """Validate the IP entered"""
        ip_range = self.ip_entry_row.get_text().strip()
        is_valid, message = self.scanner.validate_ip_range(ip_range)
        if not is_valid:
            self.show_toast(_(message))
        return is_valid

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/results_page.ui')
class ResultsPage(Adw.NavigationPage):
    """Results page for displaying scan results"""
    __gtype_name__ = 'ResultsPage'

    results_title = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    rescan_button = Gtk.Template.Child()
    results_stack = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    timer_label = Gtk.Template.Child()
    flow_box = Gtk.Template.Child()
    empty_page = Gtk.Template.Child()
    error_page = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.home_page = None

        # Timer variables
        self.scan_start_time = None
        self.timer_source_id = None

    def connect_home_page(self, home_page):
        self.home_page = home_page

    def start_timer(self):
        """Start the scan timer"""
        self.scan_start_time = time.time()
        # Update timer every second
        self.timer_source_id = GLib.timeout_add(1000, self.update_timer)

    def stop_timer(self):
        """Stop the scan timer"""
        if self.timer_source_id:
            GLib.source_remove(self.timer_source_id)
            self.timer_source_id = None

    def update_timer(self):
        """Update the timer display"""
        if self.scan_start_time:
            elapsed = time.time() - self.scan_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            timer_text = _("Time Elapsed: {minutes:02d}:{seconds:02d}").format(
                minutes=minutes,
                seconds=seconds
            )
            self.timer_label.set_text(timer_text)
        return True  # Continue calling this function

    def on_progress_update(self, hosts_scanned, total_hosts):
        """Handle progress updates from the scanner"""
        progress_text = _("Hosts Scanned: {scanned}/{total}").format(
            scanned=hosts_scanned,
            total=total_hosts
        )
        self.progress_label.set_text(progress_text)

    def start_scan(self, ip_range):
        self.rescan_button.set_sensitive(False)
        self.rescan_button.set_label(_("Scanning..."))
        self.stop_button.set_visible(True)  # Show stop button during scan

        self.clear_results()

        self.results_stack.set_visible_child_name("loading")
        self.progress_label.set_text(_("Preparing scan..."))
        self.timer_label.set_text(_("Time Elapsed: 00:00"))

        # Start the timer and spinner
        self.start_timer()

        self.results_title.set_subtitle(_("Scanning ") + ip_range + "...")

        self.scanner.scan_network(
            ip_range,
            self.on_scan_complete,
            self.on_scan_error,
            self.on_progress_update
        )

    def clear_results(self):
        child = self.flow_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flow_box.remove(child)
            child = next_child

    @Gtk.Template.Callback()
    def on_stop_clicked(self, button):
        """Handle stop scanning button click"""
        self.scanner.stop_scan()
        self.stop_button.set_visible(False)
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))

        # Stop the timer and spinner
        self.stop_timer()

        # Show partial results if any devices were found
        if self.scanner.get_partial_results():
            devices = self.scanner.get_partial_results()
            for device in devices:
                card = DeviceCard(device)
                self.flow_box.append(card)

            self.results_stack.set_visible_child_name("devices")
            self.results_title.set_subtitle(_("Scan stopped - Found {count} devices").format(count=len(devices)))
            self.show_toast(_("Scan stopped. Found {count} devices so far.").format(count=len(devices)))
        else:
            self.results_stack.set_visible_child_name("empty")
            self.results_title.set_subtitle(_("Scan stopped - No devices found"))
            self.show_toast(_("Scan stopped. No devices found."))

    @Gtk.Template.Callback()
    def on_rescan_clicked(self, button):
        if self.home_page:
            ip_range = self.home_page.ip_entry_row.get_text().strip()
            if ip_range and self.home_page.validate_ip_range():
                self.start_scan(ip_range)
            else:
                self.navigation_view.pop()

    def on_scan_complete(self, devices):
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))
        self.stop_button.set_visible(False)  # Hide stop button when scan completes

        # Stop the timer and spinner
        self.stop_timer()

        if devices:
            for device in devices:
                card = DeviceCard(device)
                self.flow_box.append(card)

            self.results_stack.set_visible_child_name("devices")
            self.results_title.set_subtitle(_("Found {count} devices").format(count=len(devices)))
            self.show_toast(_("Found {count} devices on the network.").format(count=len(devices)))
        else:
            self.results_stack.set_visible_child_name("empty")
            self.results_title.set_subtitle(_("No devices found"))
            self.show_toast(_("No devices found in the specified range"))

    def on_scan_error(self, error_message):
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))
        self.stop_button.set_visible(False)  # Hide stop button on error

        # Stop the timer and spinner
        self.stop_timer()

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(_("Error: ") + error_message)
        self.results_title.set_subtitle(_("An error occurred!"))
        self.show_toast(_("Error: ") + error_message, 5)

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
