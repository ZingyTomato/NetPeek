# pages.py
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
import time
import csv
from datetime import datetime, timedelta
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GObject

from .widgets import DeviceCard, PresetButton, ThemeSelector, ToastMixin
from .scanner import NetworkScanner
from .models import Device
from . import storage


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/home_page.ui')
class HomePage(ToastMixin, Adw.NavigationPage):
    """Home page with IP input functionality"""
    __gtype_name__ = 'HomePage'

    ip_entry_row = Gtk.Template.Child()
    ip_apply_button = Gtk.Template.Child()
    scan_button = Gtk.Template.Child()
    preset_box = Gtk.Template.Child()
    primary_popover = Gtk.Template.Child()
    deep_scan_row = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner, settings):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.settings = settings
        self.results_page = None

        self.primary_popover.add_child(ThemeSelector(self.settings), "theme")

        # Build compact thread count widget for the menu popover
        thread_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        thread_box.set_margin_start(12)
        thread_box.set_margin_end(12)
        thread_box.add_css_class("menu-item")

        thread_label = Gtk.Label()
        thread_label.set_label(_("Threads"))
        thread_label.set_halign(Gtk.Align.START)
        thread_label.set_valign(Gtk.Align.CENTER)
        thread_label.set_xalign(0.0)
        thread_label.set_hexpand(True)
        thread_label.add_css_class("body")
        thread_box.append(thread_label)

        thread_spin = Gtk.SpinButton()
        thread_spin.set_range(1, 500)
        thread_spin.set_value(self.settings.get_int('thread-count'))
        thread_spin.set_increments(10, 50)
        thread_spin.set_valign(Gtk.Align.CENTER)
        thread_spin.connect("notify::value", lambda s, _: self._on_thread_count_changed(s))
        thread_box.append(thread_spin)

        self.primary_popover.add_child(thread_box, "thread_count")

        self._setup_apply_button_focus(self.ip_entry_row, self.ip_apply_button)

        self.setup_presets()

        # Bind deep scan switch to GSettings
        self.deep_scan_row.set_active(self.settings.get_boolean('deep-scan'))
        self.deep_scan_row.connect('notify::active', self._on_deep_scan_toggled)

        last_range = self.settings.get_string('last-ip-range')
        if last_range:
            self.ip_entry_row.set_text(last_range)
        else:
            detected_range = NetworkScanner.get_local_ip_range()
            self.ip_entry_row.set_text(detected_range)

        # On launch, drop the default focus and text selection so the IP entry
        # isn't highlighted as if its contents were selected.
        GLib.idle_add(self._reset_launch_highlight)

    def _reset_launch_highlight(self):
        self._clear_focus()
        self.ip_entry_row.set_position(-1)
        return GLib.SOURCE_REMOVE

    def _clear_focus(self):
        root = self.get_root()
        if root:
            root.set_focus(None)
        return GLib.SOURCE_REMOVE

    def _setup_apply_button_focus(self, row, button):
        """Reveal a row's apply button whenever that row holds keyboard focus"""
        controller = Gtk.EventControllerFocus()
        controller.connect("enter", lambda c: button.set_visible(True))
        controller.connect("leave", lambda c: button.set_visible(False))
        row.add_controller(controller)

    def connect_results_page(self, results_page):
        self.results_page = results_page

    def setup_presets(self):
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

    def auto_detect_network(self):
        detected_range = NetworkScanner.get_local_ip_range()
        self.ip_entry_row.set_text(detected_range)

    def _on_deep_scan_toggled(self, switch, _pspec):
        self.settings.set_boolean('deep-scan', switch.get_active())

    def _on_thread_count_changed(self, spin):
        self.scanner.set_max_workers(int(spin.get_value()))
        self.settings.set_int('thread-count', int(spin.get_value()))

    @Gtk.Template.Callback()
    def on_scan_clicked(self, button):
        """Start scan when 'Scan My Network' is clicked"""
        if not self.validate_ip_range():
            return
        ip_range = self.ip_entry_row.get_text().strip()
        self.settings.set_string('last-ip-range', ip_range)
        if self.results_page:
            self.navigation_view.push(self.results_page)
            self.results_page.start_scan(ip_range, deep_scan=self.deep_scan_row.get_active())

    @Gtk.Template.Callback()
    def on_ip_range_apply(self, _widget):
        """When the apply button is clicked or Enter is pressed in the IP entry"""
        self.validate_ip_range()
        self._clear_focus()
        self.ip_entry_row.set_position(-1)

    def on_auto_detect_clicked(self, button):
        self.auto_detect_network()

    def on_preset_clicked(self, button, preset_range):
        self.ip_entry_row.set_text(preset_range)

    def validate_ip_range(self):
        ip_range = self.ip_entry_row.get_text().strip()
        is_valid, message = self.scanner.validate_ip_range(ip_range)
        if not is_valid:
            self.show_toast(_(message))
        return is_valid


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/results_page.ui')
class ResultsPage(ToastMixin, Adw.NavigationPage):
    """Results page for displaying scan results"""
    __gtype_name__ = 'ResultsPage'

    page_breakpoint_bin = Gtk.Template.Child()
    results_header = Gtk.Template.Child()
    action_box = Gtk.Template.Child()
    bottom_bar = Gtk.Template.Child()
    results_title = Gtk.Template.Child()
    stop_button = Gtk.Template.Child()
    stop_button_content = Gtk.Template.Child()
    rescan_button = Gtk.Template.Child()
    rescan_button_content = Gtk.Template.Child()
    export_button = Gtk.Template.Child()
    view_toggle_button = Gtk.Template.Child()
    sort_menu_button = Gtk.Template.Child()
    sort_list = Gtk.Template.Child()
    sort_row_known = Gtk.Template.Child()
    sort_row_ip = Gtk.Template.Child()
    sort_row_hostname = Gtk.Template.Child()
    sort_row_custom_name = Gtk.Template.Child()
    sort_row_ports = Gtk.Template.Child()
    sort_row_services = Gtk.Template.Child()
    sort_row_os = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    devices_content_stack = Gtk.Template.Child()
    results_stack = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    timer_label = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    flow_box = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    empty_page = Gtk.Template.Child()
    error_page = Gtk.Template.Child()
    scan_info_button = Gtk.Template.Child()

    def __init__(self, navigation_view, toast_overlay, scanner, settings):
        super().__init__()

        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.settings = settings
        self.home_page = None
        self.clipboard = Gdk.Display.get_default().get_clipboard()

        self.current_ip_range = ""
        self.current_scan = None

        self._deep_scan = False

        self.scan_start_time = None
        self.timer_source_id = None

        self.list_store = Gio.ListStore(item_type=Device)
        self._search_text = ""
        self._skip_blur_on_clear = False
        self._last_typed = 0.0
        self._last_pointer_press = 0.0
        self._hovering = False
        self._blur_check_id = None
        self._typing_grace = 1.0
        self._setup_column_view()
        self.flow_box.bind_model(self.filter_model, self._create_card)
        self._setup_search_behavior()
        self._setup_responsive_header()

        self._window_active_id = None
        self.connect("map", self._on_results_page_map)

        self._sort_rows = {
            self.sort_row_known: "known",
            self.sort_row_ip: "ip",
            self.sort_row_hostname: "hostname",
            self.sort_row_custom_name: "custom_name",
            self.sort_row_ports: "ports",
            self.sort_row_services: "services",
            self.sort_row_os: "os",
        }

        self.column_view.sort_by_column(self.columns["ip"], Gtk.SortType.ASCENDING)

        view_mode = self.settings.get_string('view-mode')
        is_list = view_mode == 'list'
        self.view_toggle_button.set_active(is_list)
        self.view_toggle_button.set_icon_name('view-grid-symbolic' if is_list else 'view-list-symbolic')
        self.view_toggle_button.set_tooltip_text(_("Show as grid") if is_list else _("Show as list"))
        self.view_stack.set_visible_child_name('list' if is_list else 'cards')

    def connect_home_page(self, home_page):
        self.home_page = home_page

    def _create_card(self, device):
        return DeviceCard(device, toast_overlay=self.toast_overlay)

    def _filter_func(self, item):
        """Gtk.CustomFilter match: substring search that ignores case over the
        fields shown on the device cards and list rows.
        """
        query = self._search_text
        if not query:
            return True
        haystack = " ".join((
            item.ip,
            item.hostname,
            item.custom_name,
            item.ports_display,
            item.services_display,
            item.os_display,
            "new" if not item.known else "known",
        )).lower()
        return query.lower() in haystack

    def _update_device_view(self):
        """Show the device list, a hint when nothing matches, or the empty
        state, depending on the current search query and the number of hosts.
        """
        if self.list_store.get_n_items() == 0:
            self.results_stack.set_visible_child_name("empty")
        else:
            self.results_stack.set_visible_child_name("devices")
            if self._search_text and self.filter_model.get_n_items() == 0:
                self.devices_content_stack.set_visible_child_name("no_results")
            else:
                self.devices_content_stack.set_visible_child_name("results")

    def _setup_column_view(self):
        self.sort_model = Gtk.SortListModel(model=self.list_store)
        self._filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model, filter=self._filter)

        self.column_view = Gtk.ColumnView()
        self.column_view.set_model(Gtk.NoSelection(model=self.filter_model))
        self.column_view.set_show_row_separators(True)
        self.column_view.set_show_column_separators(True)
        self.list_view.set_child(self.column_view)

        self.columns = {
            "known": self._add_status_column(),
            "ip": self._add_ip_column(),
            "hostname": self._add_hostname_column(),
            "custom_name": self._add_custom_name_column(),
            "ports": self._add_simple_column(_("Ports"), "ports-display", lambda d: d.ports_display, wrap=True, width=180),
            "services": self._add_simple_column(_("Services"), "services-display", lambda d: d.services_display, wrap=True, width=160),
            "os": self._add_simple_column(_("System Information"), "os-display", lambda d: d.os_display, wrap=True, width=180),
        }

        self.sort_model.set_sorter(self.column_view.get_sorter())
        self.column_view.get_sorter().connect("changed", lambda *_: self._update_sort_indicator())

    def _add_status_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_status_setup)
        factory.connect("bind", self.on_status_bind)
        column = Gtk.ColumnViewColumn(title="", factory=factory)
        column.set_fixed_width(50)
        column.set_sorter(Gtk.NumericSorter.new(Gtk.PropertyExpression.new(Device, None, "known-int")))
        self.column_view.append_column(column)
        return column

    def on_status_setup(self, factory, list_item):
        icon = Gtk.Image()
        icon.set_margin_start(8)
        icon.set_margin_end(8)
        list_item.set_child(icon)

    def on_status_bind(self, factory, list_item):
        icon = list_item.get_child()
        item = list_item.get_item()

        if not item.known:
            icon.set_from_icon_name("starred-symbolic")
            icon.set_tooltip_text(_("New device"))
            icon.add_css_class("accent")
        else:
            icon.set_from_icon_name("network-wireless-signal-excellent-symbolic")
            icon.set_tooltip_text(_("Known device"))
            icon.remove_css_class("accent")

    def _add_ip_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_ip_setup)
        factory.connect("bind", self.on_ip_bind)
        column = Gtk.ColumnViewColumn(title=_("IP Address"), factory=factory)
        column.set_fixed_width(170)
        column.set_resizable(True)
        column.set_sorter(Gtk.NumericSorter.new(Gtk.PropertyExpression.new(Device, None, "ip-sort-key")))
        self.column_view.append_column(column)
        return column

    def on_ip_setup(self, factory, list_item):
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
        box = list_item.get_child()
        label = box.get_first_child()
        copy_btn = label.get_next_sibling()
        item = list_item.get_item()

        label.set_text(item.ip)

        if hasattr(copy_btn, '_click_handler'):
            copy_btn.disconnect(copy_btn._click_handler)
        copy_btn._click_handler = copy_btn.connect(
            "clicked", lambda btn: self.copy_to_clipboard(item.ip))

    def _add_hostname_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_hostname_setup)
        factory.connect("bind", self.on_hostname_bind)
        column = Gtk.ColumnViewColumn(title=_("Hostname"), factory=factory)
        column.set_expand(True)
        column.set_sorter(Gtk.StringSorter.new(Gtk.PropertyExpression.new(Device, None, "hostname")))
        self.column_view.append_column(column)
        return column

    def on_hostname_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_ellipsize(3)
        list_item.set_child(label)

    def on_hostname_bind(self, factory, list_item):
        label = list_item.get_child()
        item = list_item.get_item()

        hostname = item.hostname if item.hostname != item.ip else _("Unknown")
        label.set_text(hostname)

    def _add_custom_name_column(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.on_custom_name_setup)
        factory.connect("bind", self.on_custom_name_bind)
        column = Gtk.ColumnViewColumn(title=_("Custom Name"), factory=factory)
        column.set_fixed_width(170)
        column.set_resizable(True)
        column.set_sorter(Gtk.StringSorter.new(Gtk.PropertyExpression.new(Device, None, "custom-name")))
        self.column_view.append_column(column)
        return column

    def on_custom_name_setup(self, factory, list_item):
        entry = Gtk.Entry()
        entry.set_margin_start(8)
        entry.set_margin_end(8)
        entry.set_placeholder_text(_("Click to set name..."))
        entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "object-select-symbolic")
        entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, _("Apply"))
        list_item.set_child(entry)

    def on_custom_name_bind(self, factory, list_item):
        """Bind custom name, keeping the entry synced live with the Device
        model

        so edits here and edits made via the card view's name row stay in
        sync without either widget knowing about the other.
        """
        entry = list_item.get_child()
        item = list_item.get_item()

        if getattr(entry, '_custom_name_binding', None):
            entry._custom_name_binding.unbind()
        entry._custom_name_binding = item.bind_property(
            "custom-name", entry, "text",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        if hasattr(entry, '_custom_name_handler'):
            entry.disconnect(entry._custom_name_handler)
        entry._custom_name_handler = entry.connect(
            "activate", lambda e: self._on_custom_name_committed(item, e))

        if hasattr(entry, '_custom_name_icon_handler'):
            entry.disconnect(entry._custom_name_icon_handler)
        entry._custom_name_icon_handler = entry.connect(
            "icon-press", lambda e, pos: self._on_custom_name_committed(item, e))

    def _on_custom_name_committed(self, item, entry):
        """Persist a custom name once the user commits (Enter or apply button)"""
        storage.set_custom_name(item.registry_key, item.custom_name)
        root = entry.get_root()
        if root:
            root.set_focus(None)
        entry.set_position(-1)

    def _add_simple_column(self, title, prop_name, display_func, wrap=False, width=None):
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, list_item):
            label = Gtk.Label(xalign=0, margin_start=8, margin_end=8)
            if wrap:
                label.set_wrap(True)
                label.set_wrap_mode(2)
            list_item.set_child(label)

        def bind(_factory, list_item):
            list_item.get_child().set_text(display_func(list_item.get_item()))

        factory.connect("setup", setup)
        factory.connect("bind", bind)

        column = Gtk.ColumnViewColumn(title=title, factory=factory)
        if width is not None:
            column.set_fixed_width(width)
            column.set_resizable(True)
        else:
            column.set_expand(True)
        column.set_sorter(Gtk.StringSorter.new(Gtk.PropertyExpression.new(Device, None, prop_name)))
        self.column_view.append_column(column)
        return column

    def _setup_responsive_header(self):
        """Move the header action buttons to a bottom bar on narrow windows.

        Breakpoint setters can only set properties, not reparent widgets, so
        the move is done from the apply/unapply signals instead.
        """
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 600sp"))
        breakpoint.connect("apply", self._move_actions_to_bottom)
        breakpoint.connect("unapply", self._move_actions_to_header)
        self.page_breakpoint_bin.add_breakpoint(breakpoint)

    def _action_buttons(self):
        child = self.action_box.get_first_child()
        while child is not None:
            if isinstance(child, (Gtk.Button, Gtk.ToggleButton, Gtk.MenuButton)):
                yield child
            child = child.get_next_sibling()

    def _move_actions_to_bottom(self, breakpoint):
        self.results_header.remove(self.action_box)
        self.action_box.set_halign(Gtk.Align.CENTER)
        self.action_box.set_hexpand(False)
        self.action_box.set_spacing(12)
        self.action_box.set_margin_top(6)
        self.action_box.set_margin_bottom(6)
        self.action_box.set_margin_start(6)
        self.action_box.set_margin_end(6)
        parent = self.scan_info_button.get_parent()
        if parent is not self.action_box:
            if parent is not None:
                parent.remove(self.scan_info_button)
            self.action_box.prepend(self.scan_info_button)
        for button in self._action_buttons():
            button.set_hexpand(False)
            button.set_halign(Gtk.Align.FILL)
        self.bottom_bar.set_child(self.action_box)
        self.bottom_bar.set_visible(True)
        self.view_toggle_button.set_visible(False)
        self.stop_button_content.set_label("")

    def _move_actions_to_header(self, breakpoint):
        self.bottom_bar.set_child(None)
        self.bottom_bar.set_visible(False)
        self.action_box.set_hexpand(False)
        self.action_box.set_halign(Gtk.Align.FILL)
        self.action_box.set_spacing(6)
        self.action_box.set_margin_top(0)
        self.action_box.set_margin_bottom(0)
        self.action_box.set_margin_start(0)
        self.action_box.set_margin_end(0)
        for button in self._action_buttons():
            button.set_hexpand(False)
            button.set_halign(Gtk.Align.FILL)
        self.view_toggle_button.set_visible(True)
        self.stop_button_content.set_label(_("Stop"))
        parent = self.scan_info_button.get_parent()
        if parent is not self.results_header:
            if parent is not None:
                parent.remove(self.scan_info_button)
            self.results_header.pack_start(self.scan_info_button)
        self.results_header.pack_end(self.action_box)

    def _apply_sort(self, column):
        sorter = self.column_view.get_sorter()
        if sorter.get_primary_sort_column() == column:
            order = (Gtk.SortType.DESCENDING
                     if sorter.get_primary_sort_order() == Gtk.SortType.ASCENDING
                     else Gtk.SortType.ASCENDING)
        else:
            order = Gtk.SortType.DESCENDING
        self.column_view.sort_by_column(column, order)
        self.sort_menu_button.popdown()

    def _update_sort_indicator(self):
        """Highlight the active sort row and show the direction on the button."""
        sorter = self.column_view.get_sorter()
        active_column = sorter.get_primary_sort_column()
        active_key = next((k for k, c in self.columns.items() if c == active_column), None)
        active_row = next((r for r, k in self._sort_rows.items() if k == active_key), None)
        self.sort_list.select_row(active_row)

        ascending = sorter.get_primary_sort_order() == Gtk.SortType.ASCENDING

        for row in self._sort_rows:
            box = row.get_child()
            icon = box.get_last_child()
            if row == active_row:
                icon.set_from_icon_name(
                    "view-sort-ascending-symbolic" if ascending else "view-sort-descending-symbolic")
                icon.set_visible(True)
            else:
                icon.set_visible(False)
        self.sort_menu_button.set_icon_name(
            "view-sort-ascending-symbolic" if ascending else "view-sort-descending-symbolic")

    @Gtk.Template.Callback()
    def on_sort_row_activated(self, listbox, row):
        key = self._sort_rows.get(row)
        if key:
            self._apply_sort(self.columns[key])

    @Gtk.Template.Callback()
    def on_view_toggle(self, button):
        is_list = button.get_active()
        button.set_icon_name('view-grid-symbolic' if is_list else 'view-list-symbolic')
        button.set_tooltip_text(_("Show as grid") if is_list else _("Show as list"))
        self.view_stack.set_visible_child_name('list' if is_list else 'cards')
        self.settings.set_string('view-mode', 'list' if is_list else 'cards')

    @Gtk.Template.Callback()
    def on_search_changed(self, entry):
        """Refilter the device list when the search query changes."""
        self._search_text = entry.get_text().strip()
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_device_view()
        if not self._search_text and not self._skip_blur_on_clear:
            now = time.monotonic()
            if now - self._last_typed > self._typing_grace or \
               now - self._last_pointer_press < 0.5:
                self._clear_search_focus()
        self._skip_blur_on_clear = False

    @Gtk.Template.Callback()
    def on_search_stopped(self, entry):
        """Clear the query on Escape (focus follows the hover rules)."""
        self._skip_blur_on_clear = True
        entry.set_text("")

    def _setup_search_behavior(self):
        """Automatic focus release for the search entry.

        The entry keeps normal behaviour where clicking focuses it; hovering
        does not steal focus.  Moving the pointer away drops focus unless
        the user is still typing (a one second grace after the last
        keystroke).  Clearing the query with the cancel icon also drops
        focus.
        """
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_search_hover_enter)
        motion.connect("leave", self._on_search_hover_leave)
        self.search_entry.add_controller(motion)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_search_key_pressed)
        self.search_entry.add_controller(keys)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_search_pointer_pressed)
        self.search_entry.add_controller(click)

    def _on_results_page_map(self, *args):
        root = self.get_root()
        if root is not None and self._window_active_id is None:
            self._window_active_id = root.connect("notify::is-active", self._on_window_active_changed)

    def _on_window_active_changed(self, window, pspec):
        if window.is_active():
            GLib.idle_add(self._clear_search_focus_if_focused)

    def _clear_search_focus_if_focused(self):
        if self.search_entry.is_focus() and \
           time.monotonic() - self._last_pointer_press > self._typing_grace:
            self._clear_search_focus()

    def _on_search_hover_enter(self, controller, x, y):
        # Track hover state only for the blur logic; hovering must not focus.
        self._hovering = True

    def _on_search_hover_leave(self, controller):
        self._hovering = False
        if self.search_entry.has_focus():
            if time.monotonic() - self._last_typed > self._typing_grace:
                self._clear_search_focus()
            else:
                self._schedule_blur_check()

    def _on_search_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            return False
        self._last_typed = time.monotonic()
        # A click before typing was a focus click, not a cancel press; only a
        # fresh press (e.g. on the clear icon) should count as cancelling.
        self._last_pointer_press = 0.0
        self._schedule_blur_check()
        return False

    def _on_search_pointer_pressed(self, gesture, n_press, x, y):
        self._last_pointer_press = time.monotonic()

    def _schedule_blur_check(self):
        """Blur the search entry shortly after the user stops typing while
        the pointer is no longer over it."""
        if self._blur_check_id is not None:
            GLib.source_remove(self._blur_check_id)
        self._blur_check_id = GLib.timeout_add(
            int(self._typing_grace * 1000), self._maybe_blur)

    def _maybe_blur(self):
        self._blur_check_id = None
        if not self._hovering and self.search_entry.has_focus():
            self._clear_search_focus()
        return GLib.SOURCE_REMOVE

    def _clear_search_focus(self):
        root = self.get_root()
        if root:
            root.set_focus(None)

    def copy_to_clipboard(self, text):
        self.clipboard.set(text)
        self.show_toast(_("Copied {ip} to the clipboard").format(ip=text), 2)

    @Gtk.Template.Callback()
    def on_export_clicked(self, button):
        """Export scan results to CSV"""
        if self.list_store.get_n_items() == 0:
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
                fieldnames = ['IP Address', 'Hostname', 'Custom Name',
                              'Open Ports', 'Services', 'System Information', 'Status']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for device in self.list_store:
                    writer.writerow({
                        'IP Address': device.ip,
                        'Hostname': device.hostname,
                        'Custom Name': device.custom_name,
                        'Open Ports': device.ports_display,
                        'Services': device.services_display,
                        'System Information': device.os_display,
                        'Status': _("Known") if device.known else _("New"),
                    })

            filename = Path(file_path).name
            toast = Adw.Toast(title=_("Successfully exported to ") + filename)
            toast.set_timeout(5)
            toast.set_button_label(_("Open Folder"))
            toast.connect("button-clicked", self._on_open_export_folder, file_path)
            self.toast_overlay.add_toast(toast)
        except Exception as e:
            self.show_toast(_("Export failed: ") + str(e), 5)

    def _on_open_export_folder(self, toast, file_path):
        """Open the system file manager at the exported CSV"""
        launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(file_path))
        launcher.open_containing_folder(self.get_root(), None, None)

    def start_timer(self):
        self.scan_start_time = time.time()
        self.timer_source_id = GLib.timeout_add(1000, self.update_timer)

    def stop_timer(self):
        if self.timer_source_id:
            GLib.source_remove(self.timer_source_id)
            self.timer_source_id = None

    def _scan_duration(self):
        if self.scan_start_time:
            return round(time.time() - self.scan_start_time)
        return 0

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
        progress_text = _("Hosts Scanned: {scanned}/{total}").format(
            scanned=hosts_scanned,
            total=total_hosts
        )
        self.progress_label.set_text(progress_text)

    def start_scan(self, ip_range, deep_scan=False):
        self.current_ip_range = ip_range
        self._deep_scan = deep_scan
        self.current_scan = None
        self.scan_info_button.set_sensitive(False)

        self.rescan_button.set_sensitive(False)
        self.rescan_button_content.set_label(_("Scanning..."))
        self.stop_button.set_visible(True)
        self.export_button.set_sensitive(False)
        self.view_toggle_button.set_sensitive(False)
        self.sort_menu_button.set_sensitive(False)

        self.list_store.remove_all()

        # Switch to the loading page instantly.  A crossfade would briefly
        # keep the previous devices view, including the search bar, on
        # screen.
        self.results_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.results_stack.set_visible_child_name("loading")
        self.results_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.progress_label.set_text(_("Preparing scan..."))
        self.timer_label.set_text(_("Time Elapsed: 00:00"))

        self.start_timer()

        scan_mode = _("Deep scanning") if deep_scan else _("Scanning")
        self.results_title.set_subtitle(f"{scan_mode}: {ip_range}")

        self.scanner.scan_network(
            ip_range,
            self.on_scan_complete,
            self.on_scan_error,
            self.on_progress_update,
            deep_scan=deep_scan,
        )

    @Gtk.Template.Callback()
    def on_stop_clicked(self, button):
        self.scanner.stop_scan()
        self.stop_button.set_visible(False)
        self.rescan_button.set_sensitive(True)
        self.rescan_button_content.set_label(_("Rescan"))
        self.view_toggle_button.set_sensitive(True)
        self.sort_menu_button.set_sensitive(True)

        self.stop_timer()

        partial = self.scanner.get_partial_results()
        if partial:
            annotated, scan = storage.record_scan(self.current_ip_range, partial, deep_scan=self._deep_scan, duration_seconds=self._scan_duration())
            self.current_scan = scan
            self.scan_info_button.set_sensitive(True)
            self._display_devices(annotated)
            scan_mode = _("Deep") + " · " if self._deep_scan else ""
            self.results_title.set_subtitle(scan_mode + _("Scan stopped - Found {count} devices").format(count=len(annotated)))
            self.export_button.set_sensitive(True)
        else:
            self.current_scan = None
            self.scan_info_button.set_sensitive(False)
            self._display_devices([])
            self.results_title.set_subtitle(_("Scan stopped - No devices found"))
            self.view_toggle_button.set_sensitive(False)
            self.export_button.set_sensitive(False)
            self.sort_menu_button.set_sensitive(False)

    @Gtk.Template.Callback()
    def on_rescan_clicked(self, button):
        if not self.current_ip_range:
            self.navigation_view.pop()
            return

        is_valid, message = self.scanner.validate_ip_range(self.current_ip_range)
        if is_valid:
            self.start_scan(self.current_ip_range, deep_scan=self._deep_scan)
        else:
            self.show_toast(_(message))

    def load_from_history(self, scan):
        """Load a previously saved scan without rescanning"""
        self.current_scan = scan
        ip_range = scan.get('ip_range', '')
        deep_scan = scan.get('deep_scan', False)
        devices_data = scan.get('devices', [])
        self.current_ip_range = ip_range
        self._deep_scan = deep_scan
        scan_mode = _("Deep") + " · " if deep_scan else ""
        self.results_title.set_subtitle(scan_mode + _("Loaded from history: ") + ip_range)
        devices_data = storage.apply_custom_names(devices_data)
        self._display_devices(devices_data)
        self.export_button.set_sensitive(bool(devices_data))
        self.view_toggle_button.set_sensitive(bool(devices_data))
        self.sort_menu_button.set_sensitive(bool(devices_data))
        self.scan_info_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def on_scan_info_clicked(self, button):
        if self.current_scan:
            ScanMetadataDialog(self.current_scan).present(self)

    def _display_devices(self, devices_data):
        """Populate the shared list store and switch to the right stack page"""
        # Every scan view starts with a clean search query, so queries never
        # carry over between scans (regular, rescan, or loaded from history).
        self.search_entry.set_text("")
        self.list_store.remove_all()
        for data in devices_data:
            self.list_store.append(Device(data))

        has_services = any(device.services_display for device in self.list_store)
        self.columns["services"].set_visible(has_services)
        self.sort_row_services.set_visible(has_services)

        has_os = any(device.deep_scanned for device in self.list_store)
        self.columns["os"].set_visible(has_os)
        self.sort_row_os.set_visible(has_os)

        self._update_device_view()
        self._clear_search_focus()
        GLib.idle_add(self._clear_search_focus)

    def on_scan_complete(self, devices):
        self.rescan_button.set_sensitive(True)
        self.rescan_button_content.set_label(_("Rescan"))
        self.stop_button.set_visible(False)
        self.export_button.set_sensitive(True)
        self.view_toggle_button.set_sensitive(True)
        self.sort_menu_button.set_sensitive(True)

        self.stop_timer()

        if devices:
            annotated, scan = storage.record_scan(self.current_ip_range, devices, deep_scan=self._deep_scan, duration_seconds=self._scan_duration())
            self.current_scan = scan
            self.scan_info_button.set_sensitive(True)
            self._display_devices(annotated)
            scan_mode = _("Deep") + " · " if self._deep_scan else ""
            self.results_title.set_subtitle(scan_mode + _("Found {count} devices").format(count=len(annotated)))
        else:
            self.current_scan = None
            self.scan_info_button.set_sensitive(False)
            self._display_devices([])
            self.results_title.set_subtitle(_("No devices found"))
            self.view_toggle_button.set_sensitive(False)
            self.export_button.set_sensitive(False)
            self.sort_menu_button.set_sensitive(False)

    def on_scan_error(self, error_message):
        self.rescan_button.set_sensitive(True)
        self.rescan_button_content.set_label(_("Rescan"))
        self.stop_button.set_visible(False)
        self.view_toggle_button.set_sensitive(False)
        self.sort_menu_button.set_sensitive(False)

        self.stop_timer()

        self.current_scan = None
        self.scan_info_button.set_sensitive(False)

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(_("Error: ") + error_message)
        self.results_title.set_subtitle(_("An error occurred!"))
        self.show_toast(_("Error: ") + error_message, 5)


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/history_dialog.ui')
class HistoryDialog(Adw.Dialog):
    """Dialog listing previous scans grouped by date"""
    __gtype_name__ = 'HistoryDialog'

    history_stack = Gtk.Template.Child()
    history_list = Gtk.Template.Child()
    history_scrolled = Gtk.Template.Child()
    scroll_top_button = Gtk.Template.Child()

    # Persist scroll position across dialog instances
    _saved_scroll_y = 0

    def __init__(self, on_select, **kwargs):
        super().__init__(**kwargs)
        self._on_select = on_select
        self.connect('closed', self._on_closed)
        self._populate()
        self._connect_scroll()

    def _connect_scroll(self):
        """Show the scroll to top button when the list is scrolled down."""
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            vadj.connect('value-changed', self._on_scroll)

    def _on_scroll(self, vadj):
        self.scroll_top_button.set_visible(vadj.get_value() > 100)

    def _on_closed(self, _dialog):
        """Save scroll position before the dialog is destroyed."""
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            HistoryDialog._saved_scroll_y = vadj.get_value()

    def _restore_scroll(self):
        """Restore the saved scroll position after rebuilding the list."""
        vadj = self.history_scrolled.get_vadjustment()
        if vadj and HistoryDialog._saved_scroll_y > 0:
            vadj.set_value(min(HistoryDialog._saved_scroll_y, vadj.get_upper() - vadj.get_page_size()))
        return False

    @staticmethod
    def _make_header_row(title):
        """Create a date section header compatible with all Libadwaita versions."""
        label = Gtk.Label(label=title)
        label.set_halign(Gtk.Align.START)
        label.set_margin_start(16)
        label.set_margin_end(16)
        label.set_margin_top(24)
        label.set_margin_bottom(6)
        label.add_css_class('heading')
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        row.set_can_focus(False)
        row.set_child(label)
        return row

    @staticmethod
    def _format_date_header(iso_string):
        """Parse ISO timestamp and return a human readable date header."""
        try:
            dt = datetime.fromisoformat(iso_string)
            local_dt = dt.astimezone()
            today = datetime.now(local_dt.tzinfo).date()
            scan_date = local_dt.date()
            if scan_date == today:
                return _("Today")
            if scan_date == today - timedelta(days=1):
                return _("Yesterday")
            # Use GLib.DateTime so date formatting follows the locale
            gdt = GLib.DateTime.new_local(
                local_dt.year, local_dt.month, local_dt.day, 0, 0, 0
            )
            if local_dt.year != today.year:
                return gdt.format('%A, %B %d, %Y')
            return gdt.format('%A, %B %d')
        except ValueError:
            return iso_string

    def _populate(self):
        scans = storage.load_scans()
        if not scans:
            self.history_stack.set_visible_child_name('empty')
            return

        self.history_stack.set_visible_child_name('list')

        GLib.idle_add(self._restore_scroll)

        # Group scans by date (storage is already newest first)
        groups = {}
        for scan in scans:
            ts = scan.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts)
                date_key = dt.astimezone().date().isoformat()
            except ValueError:
                date_key = ts
            groups.setdefault(date_key, []).append(scan)

        # Sort date groups newest first
        for date_key in sorted(groups.keys(), reverse=True):
            scans_in_group = groups[date_key]
            header = self._make_header_row(
                self._format_date_header(scans_in_group[0].get('timestamp', ''))
            )
            self.history_list.append(header)
            for scan in scans_in_group:
                self.history_list.append(self._build_row(scan))

    def _build_row(self, scan):
        row = Adw.ActionRow()
        row.set_title(scan.get('ip_range', ''))
        device_count = len(scan.get('devices', []))
        try:
            ts_dt = datetime.fromisoformat(scan.get('timestamp', ''))
            time_str = ts_dt.astimezone().strftime('%H:%M')
        except ValueError:
            time_str = ""
        deep_suffix = " · " + _("Deep") if scan.get("deep_scan", False) else ""
        row.set_subtitle(_("{time} · {count} devices{deep}").format(
            time=time_str, count=device_count, deep=deep_suffix))
        row.set_activatable(True)
        row.scan_data = scan

        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_tooltip_text(_("Delete this scan"))
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.add_css_class('flat')
        delete_button.connect('clicked', self._on_delete_clicked, row)
        row.add_suffix(delete_button)

        row.add_suffix(Gtk.Image.new_from_icon_name('go-next-symbolic'))
        return row

    def _on_delete_clicked(self, button, row):
        scan_data = getattr(row, 'scan_data', None)
        if not scan_data:
            return

        storage.delete_scan(scan_data.get('timestamp', ''))

        # Find the header row above this scan row
        header = row.get_prev_sibling()
        self.history_list.remove(row)

        # If the header's section is now empty, remove the header too
        if header is not None and not header.get_selectable():
            next_sibling = header.get_next_sibling()
            if next_sibling is None or not next_sibling.get_selectable():
                self.history_list.remove(header)

        # Check if any selectable (scan) rows remain
        has_scan = False
        child = self.history_list.get_first_child()
        while child is not None:
            if child.get_selectable():
                has_scan = True
                break
            child = child.get_next_sibling()
        if not has_scan:
            self.history_stack.set_visible_child_name('empty')

    @Gtk.Template.Callback()
    def on_scan_row_activated(self, listbox, row):
        # Skip header rows; they are not activatable
        if not row.get_selectable():
            return
        scan_data = getattr(row, 'scan_data', None)
        if scan_data:
            self._on_select(scan_data)
            self.close()

    @Gtk.Template.Callback()
    def on_scroll_top_clicked(self, button):
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            vadj.set_value(0)


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/scan_metadata_dialog.ui')
class ScanMetadataDialog(Adw.Dialog):
    __gtype_name__ = 'ScanMetadataDialog'

    timestamp_row = Gtk.Template.Child()
    scan_type_row = Gtk.Template.Child()
    duration_row = Gtk.Template.Child()
    new_count_row = Gtk.Template.Child()
    known_count_row = Gtk.Template.Child()

    def __init__(self, scan, **kwargs):
        super().__init__(**kwargs)
        ts = scan.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(ts).astimezone()
            gdt = GLib.DateTime.new_local(
                dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
            )
            self.timestamp_row.set_subtitle(gdt.format('%A, %B %d, %Y · %H:%M') or ts)
        except ValueError:
            self.timestamp_row.set_subtitle(ts)
        self.scan_type_row.set_subtitle(_("Deep") if scan.get('deep_scan', False) else _("Standard"))
        duration = scan.get('duration_seconds') or 0
        if duration:
            self.duration_row.set_visible(True)
            self.duration_row.set_subtitle(self._format_duration(duration))
        devices = scan.get('devices', [])
        self.new_count_row.set_subtitle(str(sum(1 for d in devices if not d.get('known', False))))
        self.known_count_row.set_subtitle(str(sum(1 for d in devices if d.get('known', False))))

    @staticmethod
    def _format_duration(seconds):
        seconds = int(seconds)
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            if minutes:
                return _("{minutes} min {seconds} s").format(minutes=minutes, seconds=secs)
            return _("{seconds} s").format(seconds=secs)
        hours, minutes = divmod(minutes, 60)
        return _("{hours} h {minutes} min").format(hours=hours, minutes=minutes)
