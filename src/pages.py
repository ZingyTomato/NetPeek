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
import csv
import json
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GObject

from .widgets import DeviceCard, PresetButton
from .scanner import NetworkScanner

@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/home_page.ui')
class HomePage(Adw.NavigationPage):
    """Home page with IP input functionality"""
    __gtype_name__ = 'HomePage'

    ip_entry_row = Gtk.Template.Child()
    scan_button = Gtk.Template.Child()
    preset_box = Gtk.Template.Child()
    thread_spinner = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.results_page = None

        self.thread_count_timeout_id = None

        self.setup_presets()

    def connect_results_page(self, results_page):
        self.results_page = results_page

    def setup_presets(self):
        """Setup preset IP range buttons and auto detect"""
        auto_button = Gtk.Button()
        auto_button.set_label(_("Auto-detect"))
        auto_button.set_tooltip_text(_("Automatically detect your local network"))
        auto_button.add_css_class("pill")
        auto_button.add_css_class("suggested-action")
        auto_button.connect('clicked', self.on_auto_detect_clicked)
        self.preset_box.append(auto_button)

        presets = [
            ("192.168.1.0/24", _("Home Network (192.168.1.x)")),
            ("192.168.0.0/24", _("Home Network (192.168.0.x)")),
            ("10.0.0.0/24", _("Corporate (10.0.0.x)")),
            ("172.16.0.0/24", _("Private (172.16.0.x)"))
        ]

        for preset_range, tooltip in presets:
            preset_button = PresetButton(preset_range, tooltip, self.on_preset_clicked)
            self.preset_box.append(preset_button)

        self.ip_entry_row.set_text(NetworkScanner.get_local_ip_range())

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

    @Gtk.Template.Callback()
    def on_thread_count_changed(self, spinner):
        """When thread count spinner value changes"""
        thread_count = int(spinner.get_value())
        self.scanner.set_max_workers(thread_count)

        if self.thread_count_timeout_id:
            GLib.source_remove(self.thread_count_timeout_id)

        self.thread_count_timeout_id = GLib.timeout_add(500, self.show_thread_count_toast, thread_count)

    def show_thread_count_toast(self, thread_count):
        """Show toast for thread count change"""
        self.show_toast(_("Thread count set to: ") + str(thread_count), 2)
        self.thread_count_timeout_id = None
        return False  # Don't repeat

    def on_auto_detect_clicked(self, button):
        """Auto-detect local network IP range"""
        detected_range = NetworkScanner.get_local_ip_range()
        self.ip_entry_row.set_text(detected_range)
        self.show_toast(_("Auto-detected IP range: ") + detected_range, 2)

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
    export_button = Gtk.Template.Child()
    view_toggle = Gtk.Template.Child()
    results_stack = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    timer_label = Gtk.Template.Child()
    flow_box = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    empty_page = Gtk.Template.Child()
    error_page = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.home_page = None
        self.clipboard = Gdk.Display.get_default().get_clipboard()

        self.current_devices = []
        self.current_view = "grid"

        self.scan_start_time = None
        self.timer_source_id = None

        self.setup_list_view()

    def connect_home_page(self, home_page):
        self.home_page = home_page

    def setup_list_view(self):
        """Setup the list view with columns"""
        self.list_store = Gio.ListStore.new(DeviceListItem)

        selection_model = Gtk.NoSelection.new(self.list_store)

        self.column_view = Gtk.ColumnView()
        self.column_view.set_model(selection_model)
        self.column_view.set_show_row_separators(True)
        self.column_view.set_show_column_separators(True)

        status_factory = Gtk.SignalListItemFactory()
        status_factory.connect("setup", self.on_status_setup)
        status_factory.connect("bind", self.on_status_bind)
        status_column = Gtk.ColumnViewColumn.new("", status_factory)
        status_column.set_fixed_width(50)
        self.column_view.append_column(status_column)

        ip_factory = Gtk.SignalListItemFactory()
        ip_factory.connect("setup", self.on_ip_setup)
        ip_factory.connect("bind", self.on_ip_bind)
        ip_column = Gtk.ColumnViewColumn.new(_("IP Address"), ip_factory)
        ip_column.set_expand(True)
        self.column_view.append_column(ip_column)

        hostname_factory = Gtk.SignalListItemFactory()
        hostname_factory.connect("setup", self.on_hostname_setup)
        hostname_factory.connect("bind", self.on_hostname_bind)
        hostname_column = Gtk.ColumnViewColumn.new(_("Hostname"), hostname_factory)
        hostname_column.set_expand(True)
        self.column_view.append_column(hostname_column)

        custom_name_factory = Gtk.SignalListItemFactory()
        custom_name_factory.connect("setup", self.on_custom_name_setup)
        custom_name_factory.connect("bind", self.on_custom_name_bind)
        custom_name_column = Gtk.ColumnViewColumn.new(_("Custom Name"), custom_name_factory)
        custom_name_column.set_expand(True)
        self.column_view.append_column(custom_name_column)

        ports_factory = Gtk.SignalListItemFactory()
        ports_factory.connect("setup", self.on_ports_setup)
        ports_factory.connect("bind", self.on_ports_bind)
        ports_column = Gtk.ColumnViewColumn.new(_("Open Ports"), ports_factory)
        ports_column.set_expand(True)
        self.column_view.append_column(ports_column)

        self.list_view.set_child(self.column_view)

    def on_status_setup(self, factory, list_item):
        """Setup status indicator cell"""
        icon = Gtk.Image()
        icon.set_margin_start(8)
        icon.set_margin_end(8)
        list_item.set_child(icon)

    def on_status_bind(self, factory, list_item):
        """Bind status indicator"""
        icon = list_item.get_child()
        item = list_item.get_item()

        if item.is_new:
            icon.set_from_icon_name("starred-symbolic")
            icon.set_tooltip_text(_("New device"))
            icon.add_css_class("accent")
        else:
            icon.set_from_icon_name("network-wireless-signal-excellent-symbolic")
            icon.set_tooltip_text(_("Known device"))
            icon.remove_css_class("accent")

    def on_ip_setup(self, factory, list_item):
        """Setup IP column"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)

        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(_("Copy IP"))

        box.append(label)
        box.append(copy_btn)
        list_item.set_child(box)

    def on_ip_bind(self, factory, list_item):
        """Bind IP address"""
        box = list_item.get_child()
        label = box.get_first_child()
        copy_btn = label.get_next_sibling()
        item = list_item.get_item()

        label.set_text(item.ip)
        copy_btn.connect("clicked", lambda btn: self.copy_to_clipboard(item.ip))

    def on_hostname_setup(self, factory, list_item):
        """Setup hostname column"""
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_ellipsize(3)
        list_item.set_child(label)

    def on_hostname_bind(self, factory, list_item):
        """Bind hostname"""
        label = list_item.get_child()
        item = list_item.get_item()

        hostname = item.hostname if item.hostname != item.ip else _("Unknown")
        label.set_text(hostname)

    def on_custom_name_setup(self, factory, list_item):
        """Setup custom name column with edit capability"""
        entry = Gtk.Entry()
        entry.set_margin_start(8)
        entry.set_margin_end(8)
        entry.set_placeholder_text(_("Click to set name..."))
        list_item.set_child(entry)

    def on_custom_name_bind(self, factory, list_item):
        """Bind custom name"""
        entry = list_item.get_child()
        item = list_item.get_item()

        custom_name = self.scanner.get_custom_name(item.ip)
        entry.set_text(custom_name if custom_name else "")

        if hasattr(entry, '_custom_name_handler'):
            entry.disconnect(entry._custom_name_handler)

        entry._custom_name_handler = entry.connect("activate",
            lambda e: self.on_custom_name_changed(item.ip, e.get_text()))

    def on_custom_name_changed(self, ip, custom_name):
        """Handle custom name change"""
        self.scanner.set_custom_name(ip, custom_name)
        if custom_name:
            self.show_toast(_("Custom name saved for ") + ip, 2)
        else:
            self.show_toast(_("Custom name cleared for ") + ip, 2)

    def on_ports_setup(self, factory, list_item):
        """Setup ports column"""
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_wrap(True)
        label.set_wrap_mode(2)
        list_item.set_child(label)

    def on_ports_bind(self, factory, list_item):
        """Bind ports"""
        label = list_item.get_child()
        item = list_item.get_item()
        label.set_text(item.ports)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.clipboard.set(text)
        self.show_toast(_("Copied to clipboard: ") + text, 2)

    @Gtk.Template.Callback()
    def on_view_toggle_clicked(self, button):
        """Toggle between grid and list view"""
        if not self.current_devices:
            return

        if self.current_view == "grid":
            self.current_view = "list"
            button.set_icon_name("view-grid-symbolic")
            button.set_tooltip_text(_("Switch to Grid View"))
            self.results_stack.set_visible_child_name("list")
        else:
            self.current_view = "grid"
            button.set_icon_name("view-list-symbolic")
            button.set_tooltip_text(_("Switch to List View"))
            self.results_stack.set_visible_child_name("devices")

    @Gtk.Template.Callback()
    def on_export_clicked(self, button):
        """Export scan results to CSV"""
        if not self.current_devices:
            self.show_toast(_("No devices to export"))
            return

        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export Scan Results"))
        dialog.set_initial_name("network_scan_results.csv")

        csv_filter = Gtk.FileFilter()
        csv_filter.set_name(_("CSV Files"))
        csv_filter.add_pattern("*.csv")

        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(csv_filter)
        dialog.set_filters(filter_list)

        dialog.save(self.get_root(), None, self.on_export_response)

    def on_export_response(self, dialog, result):
        """Handle export file dialog response"""
        try:
            file = dialog.save_finish(result)
            if file:
                file_path = file.get_path()
                self.export_to_csv(file_path)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                self.show_toast(_("Export cancelled or failed"), 3)

    def export_to_csv(self, file_path):
        """Export devices to CSV file"""
        try:
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['IP Address', 'Hostname', 'Custom Name', 'Open Ports', 'Status']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for device in self.current_devices:
                    custom_name = self.scanner.get_custom_name(device['ip'])
                    is_new = self.scanner.is_new_device(device['ip'])

                    writer.writerow({
                        'IP Address': device['ip'],
                        'Hostname': device['hostname'],
                        'Custom Name': custom_name if custom_name else '',
                        'Open Ports': device['ports'],
                        'Status': 'New' if is_new else 'Known'
                    })

            filename = Path(file_path).name
            self.show_toast(_("Successfully exported to ") + filename, 3)
        except Exception as e:
            self.show_toast(_("Export failed: ") + str(e), 5)

    def start_timer(self):
        """Start the scan timer"""
        self.scan_start_time = time.time()
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
        return True

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
        self.stop_button.set_visible(True)
        self.export_button.set_sensitive(False)
        self.view_toggle.set_sensitive(False)

        self.clear_results()

        self.results_stack.set_visible_child_name("loading")
        self.progress_label.set_text(_("Preparing scan..."))
        self.timer_label.set_text(_("Time Elapsed: 00:00"))

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

        self.list_store.remove_all()

        self.current_devices = []

    @Gtk.Template.Callback()
    def on_stop_clicked(self, button):
        """Handle stop scanning button click"""
        self.scanner.stop_scan()
        self.stop_button.set_visible(False)
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))
        self.view_toggle.set_sensitive(True)

        self.stop_timer()

        if self.scanner.get_partial_results():
            devices = self.scanner.get_partial_results()
            self.display_devices(devices)
            self.results_title.set_subtitle(_("Scan stopped - Found {count} devices").format(count=len(devices)))
            self.show_toast(_("Scan stopped. Found {count} devices so far.").format(count=len(devices)))
            self.export_button.set_sensitive(True)
        else:
            self.results_stack.set_visible_child_name("empty")
            self.results_title.set_subtitle(_("Scan stopped - No devices found"))
            self.show_toast(_("Scan stopped. No devices found."))
            self.view_toggle.set_sensitive(False)
            self.export_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_rescan_clicked(self, button):
        if self.home_page:
            ip_range = self.home_page.ip_entry_row.get_text().strip()
            if ip_range and self.home_page.validate_ip_range():
                self.start_scan(ip_range)
            else:
                self.navigation_view.pop()

    def display_devices(self, devices):
        """Display devices in both grid and list views"""
        self.current_devices = devices

        new_device_count = 0

        for device in devices:
            card = DeviceCard(device_info=device, toast_overlay=self.toast_overlay)
            self.flow_box.append(card)

            is_new = self.scanner.is_new_device(device['ip'])
            if is_new:
                new_device_count += 1

            list_item = DeviceListItem(
                ip=device['ip'],
                hostname=device['hostname'],
                ports=device['ports'],
                is_new=is_new
            )
            self.list_store.append(list_item)

        self.scanner.update_cache(devices)

        if self.current_view == "list":
            self.results_stack.set_visible_child_name("list")
        else:
            self.results_stack.set_visible_child_name("devices")

        if new_device_count > 0:
            self.show_toast(_("Found {count} new devices since last scan!").format(count=new_device_count), 4)

    def on_scan_complete(self, devices):
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))
        self.stop_button.set_visible(False)
        self.export_button.set_sensitive(True)
        self.view_toggle.set_sensitive(True)

        self.stop_timer()

        if devices:
            self.display_devices(devices)
            self.results_title.set_subtitle(_("Found {count} devices").format(count=len(devices)))
            self.show_toast(_("Found {count} devices on the network.").format(count=len(devices)))
        else:
            self.results_stack.set_visible_child_name("empty")
            self.results_title.set_subtitle(_("No devices found"))
            self.show_toast(_("No devices found in the specified range"))
            self.view_toggle.set_sensitive(False)
            self.export_button.set_sensitive(False)

    def on_scan_error(self, error_message):
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label(_("Scan Again"))
        self.stop_button.set_visible(False)
        self.view_toggle.set_sensitive(True)

        self.stop_timer()

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(_("Error: ") + error_message)
        self.results_title.set_subtitle(_("An error occurred!"))
        self.show_toast(_("Error: ") + error_message, 5)

    def show_toast(self, message, timeout=3):
        toast = Adw.Toast(title=_(message))
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)


class DeviceListItem(GObject.Object):
    """Data model for list view items"""

    def __init__(self, ip="", hostname="", ports="", is_new=False):
        super().__init__()
        self.ip = ip
        self.hostname = hostname
        self.ports = ports
        self.is_new = is_new
