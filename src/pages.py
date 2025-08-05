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

class HomePage:
    """Home page with IP input functionality"""

    def __init__(self, navigation_view, toast_overlay, scanner): ## Initialize all components
        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.results_page = None

        self.page = self.create_page()

    def connect_results_page(self, results_page):
        self.results_page = results_page

    def create_page(self): ## Create the Home Page
        page = Adw.NavigationPage()
        page.set_title(_("NetPeek"))

        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        window_title = Adw.WindowTitle()
        window_title.set_title(_("NetPeek"))
        header_bar.set_title_widget(window_title)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text(_("Main Menu"))

        menu_model = Gio.Menu()
        menu_model.append(_("About"), "app.about")
        menu_model.append(_("Quit"), "app.quit")
        menu_button.set_menu_model(menu_model)
        header_bar.pack_end(menu_button)

        toolbar_view.set_content(self.create_content())

        return page

    def create_content(self): ## Add items to the home page
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(24)
        main_box.set_margin_top(48)
        main_box.set_margin_bottom(48)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_halign(Gtk.Align.CENTER)
        main_box.set_valign(Gtk.Align.CENTER)

        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        welcome_box.set_spacing(12)
        welcome_box.set_halign(Gtk.Align.CENTER)

        app_icon = Gtk.Image()
        app_icon.set_from_icon_name("network-wireless-symbolic")
        app_icon.set_pixel_size(64)
        app_icon.add_css_class("accent")
        welcome_box.append(app_icon)

        welcome_title = Gtk.Label()
        welcome_title.set_markup(f"<span size='x-large' weight='bold'>{_('Discover devices on your local network.')}</span>")
        welcome_title.set_halign(Gtk.Align.CENTER)
        welcome_box.append(welcome_title)

        main_box.append(welcome_box)
        self.setup_ip_input_section(main_box)

        self.scan_button = Gtk.Button(label=_("Scan my Network"))
        self.scan_button.add_css_class("suggested-action")
        self.scan_button.add_css_class("pill")
        self.scan_button.set_size_request(200, 48)
        self.scan_button.set_halign(Gtk.Align.CENTER)
        self.scan_button.connect('clicked', self.on_scan_clicked)
        main_box.append(self.scan_button)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(main_box)

        return scrolled

    def setup_ip_input_section(self, parent_box): ## Allow entering/picking an IP range
        self.ip_group = Adw.PreferencesGroup()
        self.ip_group.set_title(_("IP Range Configuration"))
        self.ip_group.set_description(_("Enter the IP range you want to scan:"))

        self.ip_entry_row = Adw.EntryRow()
        self.ip_entry_row.set_title(_("IP Range"))
        self.ip_entry_row.set_text("192.168.1.0/24")
        self.ip_entry_row.set_show_apply_button(True)
        self.ip_entry_row.connect('apply', self.on_ip_range_apply)
        self.ip_entry_row.connect('entry-activated', self.on_ip_range_apply)

        help_label = Gtk.Label()
        help_label.set_markup(f"<small><i>{_('Examples: 192.168.1.0/24, 10.0.0.1-50, 172.16.1.100-200')}</i></small>")
        help_label.set_halign(Gtk.Align.START)
        help_label.set_margin_top(6)
        help_label.add_css_class("dim-label")

        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preset_box.set_spacing(6)
        preset_box.set_halign(Gtk.Align.CENTER)
        preset_box.set_margin_top(12)

        presets = [
            ("192.168.1.0/24", _("Home Network (192.168.1.x)")),
            ("192.168.0.0/24", _("Home Network (192.168.0.x)")),
            ("10.0.0.0/24", _("Corporate (10.0.0.x)")),
            ("172.16.0.0/24", _("Private (172.16.0.x)"))
        ]

        for preset_range, tooltip in presets:
            preset_button = PresetButton(preset_range, tooltip, self.on_preset_clicked)
            preset_box.append(preset_button)

        self.ip_group.add(self.ip_entry_row)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        input_box.set_spacing(12)
        input_box.append(self.ip_group)
        input_box.append(help_label)
        input_box.append(preset_box)

        clamp.set_child(input_box)
        parent_box.append(clamp)

    def on_scan_clicked(self, button): ## Start scan when "Scan My Network" is clicked
        if not self.validate_ip_range():
            return
        ip_range = self.ip_entry_row.get_text().strip()
        if self.results_page:
            self.navigation_view.push(self.results_page.page)
            self.results_page.start_scan(ip_range)

    def on_ip_range_apply(self, entry_row): ## If the check mark is clicked after entering an IP
        if self.validate_ip_range():
            self.show_toast(_("Valid IP range!"), 2)

    def on_preset_clicked(self, button, preset_range): ## If one of the IP presets were clicked
        self.ip_entry_row.set_text(preset_range)
        self.show_toast(_("Set IP range to: ") + preset_range, 2)

    def validate_ip_range(self): ## Validate the IP entered
        ip_range = self.ip_entry_row.get_text().strip()
        is_valid, message = self.scanner.validate_ip_range(ip_range)
        if not is_valid:
            self.show_toast(_(message))
        return is_valid

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)

class ResultsPage:
    """Results page for displaying scan results"""

    def __init__(self, navigation_view, toast_overlay, scanner):
        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.home_page = None

        # Timer variables
        self.scan_start_time = None
        self.timer_source_id = None

        self.page = self.create_page()

    def connect_home_page(self, home_page):
        self.home_page = home_page

    def create_page(self):
        page = Adw.NavigationPage()
        page.set_title(_("Scanning in progress..."))

        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        self.results_title = Adw.WindowTitle()
        self.results_title.set_title(_("Scan Results"))
        self.results_title.set_subtitle(_("Devices found on your network:"))
        header_bar.set_title_widget(self.results_title)

        # Stop Scanning button (left side)
        self.stop_button = Gtk.Button(label=_("Stop Scanning"))
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.set_tooltip_text(_("Stop the current network scan"))
        self.stop_button.connect('clicked', self.on_stop_clicked)
        self.stop_button.set_visible(False)  # Initially hidden
        header_bar.pack_start(self.stop_button)

        # Rescan button (right side)
        self.rescan_button = Gtk.Button(label=_("Scan Again"))
        self.rescan_button.add_css_class("suggested-action")
        self.rescan_button.connect('clicked', self.on_rescan_clicked)
        header_bar.pack_end(self.rescan_button)

        toolbar_view.set_content(self.create_content())

        return page

    def create_content(self):
        self.results_stack = Gtk.Stack()
        self.results_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.results_stack.set_transition_duration(200)

        loading_page = Adw.StatusPage()
        loading_page.set_title(_("Scanning Network"))
        loading_page.set_description(_("Discovering devices on your network... (this may take a while!)"))
        loading_page.set_icon_name("network-wireless-acquiring-symbolic")

        # Create a box to hold spinner, progress counter, and timer
        loading_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        loading_content.set_spacing(12)
        loading_content.set_halign(Gtk.Align.CENTER)

        self.spinner = Adw.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.add_css_class("large")
        loading_content.append(self.spinner)

        # Add progress counter label
        self.progress_label = Gtk.Label()
        self.progress_label.set_text(_("Preparing scan..."))
        self.progress_label.add_css_class("dim-label")
        loading_content.append(self.progress_label)

        # Add timer label
        self.timer_label = Gtk.Label()
        self.timer_label.set_text(_("Time Elapsed: 00:00"))
        self.timer_label.add_css_class("dim-label")
        loading_content.append(self.timer_label)

        loading_page.set_child(loading_content)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(3)
        self.flow_box.set_min_children_per_line(1)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_margin_top(24)
        self.flow_box.set_margin_bottom(24)
        self.flow_box.set_margin_start(24)
        self.flow_box.set_margin_end(24)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window.set_child(self.flow_box)

        self.empty_page = Adw.StatusPage()
        self.empty_page.set_title(_("No Devices Found"))
        self.empty_page.set_description(_("No devices were found in the specified range!"))
        self.empty_page.set_icon_name("network-wireless-offline-symbolic")

        self.error_page = Adw.StatusPage()
        self.error_page.set_title(_("Scan Error"))
        self.error_page.set_description(_("An error occurred while scanning the network!"))
        self.error_page.set_icon_name("dialog-error-symbolic")

        self.results_stack.add_named(loading_page, "loading")
        self.results_stack.add_named(scrolled_window, "devices")
        self.results_stack.add_named(self.empty_page, "empty")
        self.results_stack.add_named(self.error_page, "error")

        self.results_stack.set_visible_child_name("loading")

        return self.results_stack

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

        # Start the timer
        self.start_timer()

        self.results_title.set_subtitle(_("Scanning ") + ip_range + "...")

        self.scanner.scan_network(
            ip_range,
            self.on_scan_complete,
            self.on_scan_error,
            self.on_progress_update  # Add progress callback
        )

    def clear_results(self):
        child = self.flow_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flow_box.remove(child)
            child = next_child

    def on_stop_clicked(self, button):
        """Handle stop scanning button click"""
        self.scanner.stop_scan()
        self.stop_button.set_visible(False)
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))

        # Stop the timer
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

        # Stop the timer
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

        # Stop the timer
        self.stop_timer()

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(_("Error: ") + error_message)
        self.results_title.set_subtitle(_("An error occurred!"))
        self.show_toast(_("Error: ") + error_message, 5)

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
