import gi
import time
import csv
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
from ..widgets import DeviceCard, DeviceMobileRow, ToastMixin
from ..models import Device
from .. import storage


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
    search_entry = Gtk.Template.Child()
    devices_content_stack = Gtk.Template.Child()
    results_stack = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    timer_label = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()
    flow_box = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    devices_breakpoint_bin = Gtk.Template.Child()
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

        self.current_ip_range = ""
        self.current_scan = None

        self._deep_scan = False

        self.scan_start_time = None
        self.timer_source_id = None

        self.list_store = Gio.ListStore(item_type=Device)
        self._search_text = ""
        self._sort_key = 'ip'
        self._sort_ascending = True
        self._setup_view_actions()
        self._setup_device_models()
        self._setup_device_list()
        self.flow_box.bind_model(self.filter_model, self._create_card)
        self._setup_responsive_header()

        self._apply_sorter()
        self.settings.connect(
            'changed::view-mode', self._on_view_mode_setting)
        self._apply_view_mode(self.settings.get_string('view-mode') == 'list')
        self._sync_sort_button_icon()

    def connect_home_page(self, home_page):
        self.home_page = home_page

    def focus_search(self):
        if self.results_stack.get_visible_child_name() == "devices":
            self.search_entry.grab_focus()

    def stop_if_scanning(self):
        if self.stop_button.get_visible():
            self.on_stop_clicked(None)
            return True
        return False

    def export_results(self):
        if self.scanner.is_scanning or self.list_store.get_n_items() == 0:
            return
        self.on_export_clicked(None)

    def toggle_view(self):
        self._view_list_action.activate(None)

    def _sync_sort_button_icon(self):
        self.sort_menu_button.set_icon_name(
            "view-sort-ascending-symbolic" if self._sort_ascending
            else "view-sort-descending-symbolic")

    def show_scan_info(self):
        if self.current_scan:
            self.on_scan_info_clicked(None)

    def _create_card(self, device):
        return DeviceCard(device, toast_overlay=self.toast_overlay)

    def _filter_func(self, item):
        """Case-insensitive substring match over visible device fields."""
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
        """Show devices, no-results hint, or empty state as needed."""
        if self.list_store.get_n_items() == 0:
            self.results_stack.set_visible_child_name("empty")
        else:
            self.results_stack.set_visible_child_name("devices")
            if self._search_text and self.filter_model.get_n_items() == 0:
                self.devices_content_stack.set_visible_child_name("no_results")
            else:
                self.devices_content_stack.set_visible_child_name("results")

    _SORT_GETTERS = {
        "known": lambda d: d.known_int,
        "ip": lambda d: d.ip_sort_key,
        "custom_name": lambda d: (d.custom_name or "").casefold(),
        "hostname": lambda d: (d.hostname or "").casefold(),
        "ports": lambda d: (d.ports_display or "").casefold(),
        "services": lambda d: (d.services_display or "").casefold(),
        "os": lambda d: (d.os_display or "").casefold(),
    }

    def _setup_device_models(self):
        self.sort_model = Gtk.SortListModel(model=self.list_store)
        self._filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.sort_model, filter=self._filter)

    def _compare_devices(self, a, b, *_args):
        getter = self._SORT_GETTERS[self._sort_key]
        va, vb = getter(a), getter(b)
        result = (va > vb) - (va < vb)
        return -result if not self._sort_ascending else result

    def _apply_sorter(self):
        self.sort_model.set_sorter(Gtk.CustomSorter.new(self._compare_devices))

    def _setup_device_list(self):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_device_row_setup)
        factory.connect("bind", self._on_device_row_bind)
        factory.connect("unbind", self._on_device_row_unbind)
        self.device_list_view = Gtk.ListView(
            model=Gtk.NoSelection(model=self.filter_model),
            factory=factory,
        )
        self.device_list_view.set_show_separators(False)
        self.device_list_view.add_css_class("mobile-device-list")
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_child(self.device_list_view)
        self.list_view.set_child(clamp)
        self.list_view.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    def _on_device_row_setup(self, factory, list_item):
        list_item.set_child(DeviceMobileRow(toast_overlay=self.toast_overlay))

    def _on_device_row_bind(self, factory, list_item):
        row = list_item.get_child()
        device = list_item.get_item()
        if row is not None and device is not None:
            row.bind_device(device)

    def _on_device_row_unbind(self, factory, list_item):
        row = list_item.get_child()
        if row is not None:
            row.unbind_device()

    def _setup_responsive_header(self):
        """Move header actions to the bottom bar on narrow windows."""
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

    def _style_action_box(self, bottom):
        box = self.action_box
        if bottom:
            box.set_halign(Gtk.Align.CENTER)
            box.set_spacing(12)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(6)
            box.set_margin_end(6)
        else:
            box.set_halign(Gtk.Align.FILL)
            box.set_spacing(6)
            box.set_margin_top(0)
            box.set_margin_bottom(0)
            box.set_margin_start(0)
            box.set_margin_end(0)
        box.set_hexpand(False)
        for button in self._action_buttons():
            button.set_hexpand(False)
            button.set_halign(Gtk.Align.FILL)

    def _reparent_scan_info(self, to_bottom):
        if to_bottom:
            parent = self.scan_info_button.get_parent()
            if parent is not self.action_box:
                if parent is not None:
                    parent.remove(self.scan_info_button)
                self.action_box.prepend(self.scan_info_button)
        else:
            parent = self.scan_info_button.get_parent()
            if parent is not self.results_header:
                if parent is not None:
                    parent.remove(self.scan_info_button)
                self.results_header.pack_start(self.scan_info_button)

    def _move_actions_to_bottom(self, breakpoint):
        self.results_header.remove(self.action_box)
        self._style_action_box(bottom=True)
        self._reparent_scan_info(to_bottom=True)
        self.bottom_bar.set_child(self.action_box)
        self.bottom_bar.set_visible(True)

    def _move_actions_to_header(self, breakpoint):
        self.bottom_bar.set_child(None)
        self.bottom_bar.set_visible(False)
        self._style_action_box(bottom=False)
        self._reparent_scan_info(to_bottom=False)
        self.results_header.pack_end(self.action_box)

    def _setup_view_actions(self):
        """Stateful actions backing the secondary view menu.

        ``view.sort-by`` (string) renders as radio items, ``view.ascending``
        and ``view.list-view`` (booleans) as check items. GTK draws the
        indicators from action state — no manual icon swapping.
        """
        self._view_action_group = Gio.SimpleActionGroup()

        self._sort_by_action = Gio.SimpleAction.new_stateful(
            "sort-by", GLib.VariantType.new("s"),
            GLib.Variant.new_string(self._sort_key))
        self._sort_by_action.connect("activate", self._on_sort_by_activate)
        self._sort_by_action.connect("change-state", self._on_sort_by_change_state)
        self._view_action_group.add_action(self._sort_by_action)

        self._ascending_action = Gio.SimpleAction.new_stateful(
            "ascending", None,
            GLib.Variant.new_boolean(self._sort_ascending))
        self._ascending_action.connect("activate", self._on_ascending_activate)
        self._view_action_group.add_action(self._ascending_action)

        self._view_list_action = Gio.SimpleAction.new_stateful(
            "list-view", None,
            GLib.Variant.new_boolean(
                self.settings.get_string('view-mode') == 'list'))
        self._view_list_action.connect("activate", self._on_list_view_activate)
        self._view_action_group.add_action(self._view_list_action)

        self.insert_action_group("view", self._view_action_group)

    def _sync_view_actions(self):
        by_state = GLib.Variant.new_string(self._sort_key)
        if self._sort_by_action.get_state() != by_state:
            self._sort_by_action.set_state(by_state)
        asc_state = GLib.Variant.new_boolean(self._sort_ascending)
        if self._ascending_action.get_state() != asc_state:
            self._ascending_action.set_state(asc_state)
        self._sync_sort_button_icon()

    def _on_sort_by_activate(self, action, parameter):
        action.change_state(parameter)

    def _on_sort_by_change_state(self, action, state):
        key = state.get_string()
        if key not in self._SORT_GETTERS:
            return
        action.set_state(state)
        self._sort_key = key
        self._apply_sorter()
        self._sync_view_actions()
        self.sort_menu_button.popdown()

    def _on_ascending_activate(self, action, _param):
        new_value = not action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(new_value))
        self._sort_ascending = new_value
        self._apply_sorter()
        self._sync_view_actions()

    def _on_list_view_activate(self, action, _param):
        new_value = not action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(new_value))
        self._apply_view_mode(new_value)

    def _on_view_mode_setting(self, settings, _key):
        self._apply_view_mode(settings.get_string('view-mode') == 'list')

    def _apply_view_mode(self, is_list):
        list_state = GLib.Variant.new_boolean(is_list)
        if self._view_list_action.get_state() != list_state:
            self._view_list_action.set_state(list_state)
        if self.view_toggle_button.get_active() != is_list:
            self.view_toggle_button.set_active(is_list)
        self.view_toggle_button.set_icon_name(
            'view-grid-symbolic' if is_list else 'view-list-symbolic')
        view_tip = _("Show as grid") if is_list else _("Show as list")
        self.view_toggle_button.set_tooltip_text(view_tip)
        self.view_toggle_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [view_tip])
        self.view_stack.set_visible_child_name('list' if is_list else 'cards')
        mode = 'list' if is_list else 'cards'
        if self.settings.get_string('view-mode') != mode:
            self.settings.set_string('view-mode', mode)

    @Gtk.Template.Callback()
    def on_view_toggle(self, button):
        self._apply_view_mode(button.get_active())

    @Gtk.Template.Callback()
    def on_search_changed(self, entry):
        """Refilter the device list when the search query changes."""
        self._search_text = entry.get_text().strip()
        self._filter.changed(Gtk.FilterChange.DIFFERENT)
        self._update_device_view()

    @Gtk.Template.Callback()
    def on_search_stopped(self, entry):
        """Clear the query on Escape; a second Escape leaves the entry."""
        if entry.get_text():
            entry.set_text("")
            return
        visible = self.view_stack.get_visible_child_name()
        target = self.list_view if visible == "list" else self.flow_box
        target.grab_focus()

    @Gtk.Template.Callback()
    def on_export_clicked(self, button):
        """Export scan results to CSV"""
        if self.list_store.get_n_items() == 0:
            self.show_toast(_("No devices to export"))
            return

        dialog = Gtk.FileDialog()
        dialog.set_title(_("Export scan results"))
        dialog.set_initial_name("network_scan_results.csv")

        csv_filter = Gtk.FileFilter()
        csv_filter.set_name(_("CSV files"))
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
            if "dismissed" in str(e).lower():
                return
            print(f"Export failed: {e}")
            self.show_toast(_("Export failed. Please try again."), 5)

    def export_to_csv(self, file_path):
        """Export devices to CSV file"""
        try:
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['IP Address', 'Hostname', 'Custom Name',
                              'Open Ports', 'Services', 'System Information', 'Status']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for i in range(self.filter_model.get_n_items()):
                    device = self.filter_model.get_item(i)
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
            toast = Adw.Toast(title=_("Successfully exported to {name}").format(
                name=filename))
            toast.set_timeout(5)
            toast.set_button_label(_("Open Folder"))
            toast.connect("button-clicked", self._on_open_export_folder, file_path)
            self.toast_overlay.add_toast(toast)
        except Exception as e:
            print(f"Export failed: {e}")
            self.show_toast(_("Export failed. Please try again."), 5)

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

    def _elapsed(self):
        if self.scan_start_time:
            return time.time() - self.scan_start_time
        return 0

    def _scan_duration(self):
        return round(self._elapsed())

    def update_timer(self):
        """Update the timer display"""
        if self.scan_start_time:
            elapsed = self._elapsed()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            timer_text = _("Time elapsed: {minutes:02d}:{seconds:02d}").format(
                minutes=minutes,
                seconds=seconds
            )
            self.timer_label.set_text(timer_text)
        return True

    def on_progress_update(self, hosts_scanned, total_hosts):
        progress_text = _("Hosts scanned: {scanned}/{total}").format(
            scanned=hosts_scanned,
            total=total_hosts
        )
        self.progress_label.set_text(progress_text)

    def _set_controls(self, scanning, has_results=True):
        self.rescan_button.set_sensitive(not scanning)
        self.rescan_button_content.set_label(_("Scanning...") if scanning else _("Rescan"))
        self.stop_button.set_visible(scanning)
        self.export_button.set_sensitive(has_results and not scanning)
        self.view_toggle_button.set_sensitive(has_results and not scanning)
        self.sort_menu_button.set_sensitive(has_results and not scanning)
        if scanning:
            self.scan_info_button.set_sensitive(False)
        state_tip = (_("Show as grid") if self.view_toggle_button.get_active()
                     else _("Show as list"))
        self.view_toggle_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [state_tip])

    def _scan_mode_prefix(self):
        return _("Deep") + " · " if self._deep_scan else ""

    def start_scan(self, ip_range, deep_scan=False):
        if self.scanner.is_scanning:
            self.show_toast(_("Scan already in progress"))
            return
        self.current_ip_range = ip_range
        self._deep_scan = deep_scan
        self.current_scan = None

        self.stop_timer()
        self._set_controls(True)
        self.search_entry.set_text("")
        self._search_text = ""
        self.list_store.remove_all()

        self.results_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.results_stack.set_visible_child_name("loading")
        self.results_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.progress_label.set_text(_("Preparing scan…"))
        self.timer_label.set_text(_("Time elapsed: 00:00"))

        self.start_timer()

        scan_mode = _("Deep scanning") if deep_scan else _("Scanning")
        self.results_title.set_subtitle(
            _("{mode} · {range}").format(mode=scan_mode, range=ip_range))

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
        self.stop_timer()

        partial = self.scanner.get_partial_results()
        if partial:
            self._finish_with_devices(partial, stopped=True)
        else:
            self._finish_empty(stopped=True)

    @Gtk.Template.Callback()
    def on_rescan_clicked(self, button):
        if self.scanner.is_scanning:
            return
        if not self.current_ip_range:
            self.navigation_view.pop()
            return

        is_valid, message = self.scanner.validate_ip_range(self.current_ip_range)
        if is_valid:
            self.start_scan(self.current_ip_range, deep_scan=self._deep_scan)
        else:
            self.show_toast(message)

    def load_from_history(self, scan):
        """Load a previously saved scan without rescanning"""
        self.scanner.stop_scan()
        self.stop_timer()
        self.current_scan = scan
        ip_range = scan.get('ip_range', '')
        deep_scan = scan.get('deep_scan', False)
        devices_data = scan.get('devices', [])
        self.current_ip_range = ip_range
        self._deep_scan = deep_scan
        self.results_title.set_subtitle(
            _("{deep}Loaded from history · {range}").format(
                deep=self._scan_mode_prefix(), range=ip_range))
        devices_data = storage.apply_custom_names(devices_data)
        self._display_devices(devices_data)
        has_results = bool(devices_data)
        self._set_controls(False, has_results)
        self.scan_info_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def on_scan_info_clicked(self, button):
        if self.current_scan:
            from .scan_info import ScanMetadataDialog
            ScanMetadataDialog(self.current_scan).present(self)

    def _display_devices(self, devices_data):
        """Populate the shared list store and switch to the right stack page"""
        self.search_entry.set_text("")
        self.list_store.remove_all()
        for data in devices_data:
            self.list_store.append(Device(data))

        self._update_device_view()

    def _finish_with_devices(self, devices, stopped=False):
        annotated, scan = storage.record_scan(
            self.current_ip_range, devices,
            deep_scan=self._deep_scan, duration_seconds=self._scan_duration())
        self.current_scan = scan
        self.scan_info_button.set_sensitive(True)
        self._display_devices(annotated)
        found = ngettext(
            "Found {count} device",
            "Found {count} devices",
            len(annotated),
        ).format(count=len(annotated))
        if stopped:
            self.results_title.set_subtitle(
                _("{deep}Scan stopped · {found}").format(
                    deep=self._scan_mode_prefix(), found=found))
        else:
            self.results_title.set_subtitle(
                _("{deep}{found}").format(
                    deep=self._scan_mode_prefix(), found=found))
        self._set_controls(False, True)

    def _finish_empty(self, stopped=False):
        self.current_scan = None
        self.scan_info_button.set_sensitive(False)
        self._display_devices([])
        if stopped:
            self.results_title.set_subtitle(_("Scan stopped · No devices found"))
        else:
            self.results_title.set_subtitle(_("No devices found"))
        self._set_controls(False, False)

    def on_scan_complete(self, devices):
        self.stop_timer()
        if devices:
            self._finish_with_devices(devices)
        else:
            self._finish_empty()

    def on_scan_error(self, error_message):
        self.stop_timer()
        self._set_controls(False, False)
        self.current_scan = None
        self.scan_info_button.set_sensitive(False)

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(error_message)
        self.results_title.set_subtitle(_("Scan failed"))
